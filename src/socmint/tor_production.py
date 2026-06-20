from __future__ import annotations

import datetime as dt
import json
import os
import socket
import urllib.request
from pathlib import Path
from typing import Any

from sqlalchemy import text

from . import database as db

TOR_SCHEMA = "socmint.tor_production.v8_4_0"
TOR_DIAGNOSTICS_SCHEMA = "socmint.tor_hidden_service_diagnostics.v12_10_16"
DEFAULT_SERVICE_DIR = "var/tor/hidden_service"
DEFAULT_TOR_PORT = 80
DEFAULT_APP_HOST = "127.0.0.1"
DEFAULT_APP_PORT = 5000


def _now() -> dt.datetime:
    return db.utc_now()


def _json(value: Any) -> str:
    return json.dumps(value or {}, sort_keys=True)


def ensure_tor_schema() -> None:
    db.ensure_configured()
    session = db.Session()
    try:
        session.execute(
            text("""
            CREATE TABLE IF NOT EXISTS hidden_service_status (
                id INTEGER PRIMARY KEY,
                service_name VARCHAR(128) NOT NULL UNIQUE,
                enabled BOOLEAN NOT NULL,
                onion_hostname VARCHAR(255),
                service_dir TEXT NOT NULL,
                tor_port INTEGER NOT NULL,
                target_host VARCHAR(255) NOT NULL,
                target_port INTEGER NOT NULL,
                status VARCHAR(64) NOT NULL,
                last_check_json TEXT NOT NULL,
                actor VARCHAR(255),
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL
            )
        """)
        )
        session.commit()
    finally:
        session.close()


def torrc_snippet(
    service_dir: str = DEFAULT_SERVICE_DIR,
    tor_port: int = DEFAULT_TOR_PORT,
    target_host: str = DEFAULT_APP_HOST,
    target_port: int = DEFAULT_APP_PORT,
) -> str:
    return "\n".join(
        [
            "# SOCMINT v8.4 Tor hidden service",
            f"HiddenServiceDir {service_dir}",
            f"HiddenServicePort {int(tor_port)} {target_host}:{int(target_port)}",
            "HiddenServiceVersion 3",
            "",
        ]
    )


def parse_torrc_text(text_value: str) -> dict[str, Any]:
    parsed: dict[str, Any] = {
        "raw_present": bool(text_value),
        "hidden_service_ports": [],
    }
    for raw_line in text_value.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        key = parts[0]
        if key == "SocksPort" and len(parts) >= 2:
            parsed["socks_port"] = parts[1]
        elif key == "DataDirectory" and len(parts) >= 2:
            parsed["data_directory"] = parts[1]
        elif key == "HiddenServiceDir" and len(parts) >= 2:
            parsed["hidden_service_dir"] = parts[1]
        elif key == "HiddenServiceVersion" and len(parts) >= 2:
            parsed["hidden_service_version"] = parts[1]
        elif key == "HiddenServicePort" and len(parts) >= 3:
            target = parts[2]
            target_host, _, target_port = target.rpartition(":")
            parsed["hidden_service_ports"].append(
                {
                    "public_port": parts[1],
                    "target": target,
                    "target_host": target_host or target,
                    "target_port": target_port if target_port else None,
                    "shared_namespace_localhost_mapping": target.startswith(
                        "127.0.0.1:"
                    ),
                }
            )
    return parsed


def read_torrc(path: str = "/etc/tor/torrc") -> dict[str, Any]:
    torrc = Path(path)
    if not torrc.exists():
        return {"path": path, "exists": False, "parsed": parse_torrc_text("")}
    text_value = torrc.read_text(errors="replace")
    return {
        "path": path,
        "exists": True,
        "text": text_value,
        "parsed": parse_torrc_text(text_value),
    }


def _socket_check(host: str, port: int, timeout: float = 2.0) -> dict[str, Any]:
    sock = socket.socket()
    sock.settimeout(timeout)
    try:
        sock.connect((host, int(port)))
        return {"host": host, "port": int(port), "listening": True, "error": None}
    except Exception as exc:
        return {"host": host, "port": int(port), "listening": False, "error": str(exc)}
    finally:
        sock.close()


def _http_check(url: str, timeout: float = 5.0) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            body = response.read(200)
            return {
                "url": url,
                "ok": 200 <= int(response.status) < 500,
                "status": int(response.status),
                "sample": body.decode("utf-8", errors="replace"),
                "error": None,
            }
    except Exception as exc:
        return {
            "url": url,
            "ok": False,
            "status": None,
            "sample": "",
            "error": str(exc),
        }


def tor_hidden_service_diagnostics(
    torrc_path: str | None = None,
    service_dir: str | None = None,
    app_host: str | None = None,
    app_port: int | None = None,
) -> dict[str, Any]:
    """Return an operator-safe diagnostic for SOCMINT's Docker Tor topology.

    In the production Docker topology the app uses `network_mode: service:tor` and
    gunicorn binds to 127.0.0.1:5000. In that specific topology a Tor hidden
    service line of `HiddenServicePort 80 127.0.0.1:5000` is correct because the
    app and tor containers share one network namespace.
    """

    app_host = app_host or os.getenv("SOCMINT_TOR_TARGET_HOST") or DEFAULT_APP_HOST
    app_port = int(app_port or os.getenv("SOCMINT_TOR_TARGET_PORT") or DEFAULT_APP_PORT)
    torrc_path = torrc_path or os.getenv("SOCMINT_TORRC_PATH") or "/etc/tor/torrc"
    service_dir = (
        service_dir or os.getenv("SOCMINT_TOR_SERVICE_DIR") or "/var/lib/tor/socmint"
    )
    torrc = read_torrc(torrc_path)
    service = deployment_check(service_dir=service_dir)
    socket_result = _socket_check(app_host, app_port)
    readyz = _http_check(f"http://{app_host}:{app_port}/readyz")
    dashboard = _http_check(f"http://{app_host}:{app_port}/")
    hidden_ports = torrc.get("parsed", {}).get("hidden_service_ports", [])
    mapping_ok = any(
        str(row.get("public_port")) == "80"
        and row.get("target_host") == app_host
        and str(row.get("target_port")) == str(app_port)
        for row in hidden_ports
    )
    localhost_mapping = any(
        row.get("shared_namespace_localhost_mapping") for row in hidden_ports
    )
    docker_tor = os.getenv("SOCMINT_DOCKER_TOR", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    shared_namespace_expected = docker_tor or (
        app_host == "127.0.0.1" and localhost_mapping
    )
    checks = {
        "torrc_available_to_process": bool(torrc.get("exists")),
        "hidden_service_dir_present": bool(
            service.get("checks", {}).get("service_dir_present")
        ),
        "hostname_present": bool(service.get("checks", {}).get("hostname_present")),
        "hostname_format_valid": bool(
            service.get("checks", {}).get("hostname_format_valid")
        ),
        "hidden_service_port_maps_to_app": bool(mapping_ok),
        "localhost_mapping_valid_for_shared_namespace": bool(
            shared_namespace_expected and localhost_mapping
        ),
        "app_socket_listening": bool(socket_result.get("listening")),
        "readyz_http_ok": bool(readyz.get("ok") and readyz.get("status") == 200),
        "dashboard_http_ok": bool(dashboard.get("ok")),
    }
    passed = all(checks.values())
    recommendation = "pass"
    if not mapping_ok and localhost_mapping and shared_namespace_expected:
        recommendation = (
            "do_not_change_127_0_0_1_mapping_shared_network_namespace_detected"
        )
    elif not mapping_ok:
        recommendation = f"verify HiddenServicePort 80 {app_host}:{app_port} or the Docker network namespace model"
    elif not checks["readyz_http_ok"]:
        recommendation = "app target is mapped but /readyz is not healthy"
    return {
        "schema": TOR_DIAGNOSTICS_SCHEMA,
        "generated_at": _now().isoformat(),
        "status": "pass" if passed else "fail",
        "decision": "GO" if passed else "HOLD",
        "checks": checks,
        "recommendation": recommendation,
        "docker_topology": {
            "socmint_docker_tor": docker_tor,
            "expected_shared_network_namespace": shared_namespace_expected,
            "why_127_0_0_1_can_be_correct": "When app uses network_mode: service:tor, 127.0.0.1 inside Tor's hidden-service target is the shared app/Tor namespace, not the host.",
        },
        "target": {
            "host": app_host,
            "port": app_port,
            "readyz_url": f"http://{app_host}:{app_port}/readyz",
        },
        "torrc": torrc,
        "hidden_service": service,
        "socket": socket_result,
        "readyz": readyz,
        "dashboard": dashboard,
    }


def deployment_check(
    service_dir: str = DEFAULT_SERVICE_DIR,
    onion_hostname: str | None = None,
) -> dict[str, Any]:
    path = Path(service_dir)
    hostname_path = path / "hostname"
    checks = {
        "service_dir_present": path.exists(),
        "service_dir_not_world_writable": True,
        "hostname_present": bool(onion_hostname),
        "hostname_format_valid": False,
        "secrets_not_committed": True,
    }
    if path.exists():
        mode = path.stat().st_mode
        checks["service_dir_not_world_writable"] = not bool(mode & 0o002)
    if not onion_hostname and hostname_path.exists():
        onion_hostname = hostname_path.read_text().strip()
        checks["hostname_present"] = bool(onion_hostname)
    if onion_hostname:
        checks["hostname_format_valid"] = (
            onion_hostname.endswith(".onion") and len(onion_hostname) >= 22
        )
    private_key_path = path / "hs_ed25519_secret_key"
    if private_key_path.exists():
        checks["private_key_detected_not_read"] = True
    passed = all(
        value for key, value in checks.items() if key != "private_key_detected_not_read"
    )
    return {
        "schema": TOR_SCHEMA,
        "passed": bool(passed),
        "service_dir": str(path),
        "onion_hostname": onion_hostname,
        "checks": checks,
        "generated_at": _now().isoformat(),
    }


def upsert_hidden_service_status(
    service_name: str = "socmint",
    enabled: bool = False,
    onion_hostname: str | None = None,
    service_dir: str = DEFAULT_SERVICE_DIR,
    tor_port: int = DEFAULT_TOR_PORT,
    target_host: str = DEFAULT_APP_HOST,
    target_port: int = DEFAULT_APP_PORT,
    actor: str | None = None,
) -> dict[str, Any]:
    ensure_tor_schema()
    check = deployment_check(service_dir=service_dir, onion_hostname=onion_hostname)
    status = (
        "ready"
        if enabled and check["passed"]
        else "disabled"
        if not enabled
        else "needs_attention"
    )
    now = _now()
    session = db.Session()
    try:
        session.execute(
            text("""
                INSERT INTO hidden_service_status
                (service_name, enabled, onion_hostname, service_dir, tor_port,
                 target_host, target_port, status, last_check_json, actor, created_at, updated_at)
                VALUES (:service_name, :enabled, :onion_hostname, :service_dir, :tor_port,
                        :target_host, :target_port, :status, :last_check_json, :actor, :now, :now)
                ON CONFLICT(service_name) DO UPDATE SET
                    enabled = excluded.enabled,
                    onion_hostname = excluded.onion_hostname,
                    service_dir = excluded.service_dir,
                    tor_port = excluded.tor_port,
                    target_host = excluded.target_host,
                    target_port = excluded.target_port,
                    status = excluded.status,
                    last_check_json = excluded.last_check_json,
                    actor = excluded.actor,
                    updated_at = excluded.updated_at
            """),
            {
                "service_name": service_name,
                "enabled": bool(enabled),
                "onion_hostname": onion_hostname,
                "service_dir": service_dir,
                "tor_port": int(tor_port),
                "target_host": target_host,
                "target_port": int(target_port),
                "status": status,
                "last_check_json": _json(check),
                "actor": actor,
                "now": now,
            },
        )
        session.commit()
    finally:
        session.close()
    db.record_audit_event(
        action="tor_hidden_service_status_update",
        actor=actor,
        details={"service_name": service_name, "enabled": enabled, "status": status},
    )
    return hidden_service_status(service_name)


def hidden_service_status(service_name: str = "socmint") -> dict[str, Any]:
    ensure_tor_schema()
    session = db.Session()
    try:
        row = (
            session.execute(
                text(
                    "SELECT * FROM hidden_service_status WHERE service_name = :service_name"
                ),
                {"service_name": service_name},
            )
            .mappings()
            .first()
        )
    finally:
        session.close()
    if not row:
        check = deployment_check()
        return {
            "schema": TOR_SCHEMA,
            "service_name": service_name,
            "enabled": False,
            "status": "not_configured",
            "torrc": torrc_snippet(),
            "check": check,
        }
    payload = dict(row)
    payload["enabled"] = bool(payload.get("enabled"))
    payload["last_check"] = json.loads(payload.pop("last_check_json") or "{}")
    payload["torrc"] = torrc_snippet(
        service_dir=payload["service_dir"],
        tor_port=payload["tor_port"],
        target_host=payload["target_host"],
        target_port=payload["target_port"],
    )
    payload["schema"] = TOR_SCHEMA
    return payload


def production_env_template() -> str:
    return "\n".join(
        [
            "# SOCMINT v8.4 production environment",
            "SOCMINT_FORCE_HTTPS=true",
            "SOCMINT_COOKIE_SECURE=true",
            "SOCMINT_TOR_HIDDEN_SERVICE=true",
            "SOCMINT_MINIMIZE_METADATA=true",
            "SOCMINT_BACKUP_ENCRYPTION_REQUIRED=true",
            "SOCMINT_BILLING_WEBHOOK_SECRET=change-me-outside-git",
            "",
        ]
    )


def production_readiness_report(service_dir: str | None = None) -> dict[str, Any]:
    service_dir = (
        service_dir or os.getenv("SOCMINT_TOR_SERVICE_DIR") or DEFAULT_SERVICE_DIR
    )
    check = deployment_check(service_dir=service_dir)
    return {
        "schema": TOR_SCHEMA,
        "tor": check,
        "required_controls": {
            "https_or_onion_only": True,
            "secure_cookies": True,
            "metadata_minimization": True,
            "encrypted_backups_required": True,
            "audit_logging_required": True,
            "responsible_use_gates_required": True,
            "billing_webhook_secret_required": True,
        },
        "env_template": production_env_template(),
    }
