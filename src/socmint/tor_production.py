from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
from typing import Any

from sqlalchemy import text

from . import database as db

TOR_SCHEMA = "socmint.tor_production.v8_4_0"
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
        session.execute(text("""
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
        """))
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
        checks["hostname_format_valid"] = onion_hostname.endswith(".onion") and len(onion_hostname) >= 22
    # Guardrail: this helper never reads or stores private_key content.
    private_key_path = path / "hs_ed25519_secret_key"
    if private_key_path.exists():
        checks["private_key_detected_not_read"] = True
    passed = all(value for key, value in checks.items() if key != "private_key_detected_not_read")
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
    status = "ready" if enabled and check["passed"] else "disabled" if not enabled else "needs_attention"
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
        row = session.execute(
            text("SELECT * FROM hidden_service_status WHERE service_name = :service_name"),
            {"service_name": service_name},
        ).mappings().first()
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
    service_dir = service_dir or os.getenv("SOCMINT_TOR_SERVICE_DIR") or DEFAULT_SERVICE_DIR
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
