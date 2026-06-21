from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA = "socmint.release_runtime_readiness.v12_10_21"
VERSION = "12.10.21"


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _http_probe(url: str, timeout: float = 4.0) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            body = response.read(300).decode("utf-8", errors="replace")
            return {
                "url": url,
                "ok": 200 <= int(response.status) < 500,
                "status_code": int(response.status),
                "body_sample": body,
                "error": None,
            }
    except urllib.error.HTTPError as exc:
        body = exc.read(300).decode("utf-8", errors="replace")
        return {
            "url": url,
            "ok": 200 <= int(exc.code) < 500,
            "status_code": int(exc.code),
            "body_sample": body,
            "error": str(exc),
        }
    except Exception as exc:
        return {
            "url": url,
            "ok": False,
            "status_code": None,
            "body_sample": "",
            "error": repr(exc),
        }


def _socket_probe(
    host: str = "127.0.0.1", port: int = 5000, timeout: float = 3.0
) -> dict[str, Any]:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return {"host": host, "port": port, "ok": True, "error": None}
    except Exception as exc:
        return {"host": host, "port": port, "ok": False, "error": repr(exc)}


def _tor_files() -> dict[str, Any]:
    torrc = Path("/etc/tor/torrc")
    hostname = Path("/var/lib/tor/socmint/hostname")
    hidden_dir = Path("/var/lib/tor/socmint")
    hostname_text = ""
    if hostname.exists():
        try:
            hostname_text = hostname.read_text(errors="replace").strip()
        except Exception:
            hostname_text = ""
    return {
        "torrc_available": torrc.is_file(),
        "hidden_service_dir_present": hidden_dir.is_dir(),
        "hostname_present": bool(hostname_text),
        "hostname": hostname_text,
        "hostname_format_valid": hostname_text.endswith(".onion")
        if hostname_text
        else False,
        "informational": True,
    }


def release_runtime_readiness(base_url: str | None = None) -> dict[str, Any]:
    base = (
        base_url or os.getenv("SOCMINT_LOCAL_BASE_URL") or "http://127.0.0.1:5000"
    ).rstrip("/")
    socket_probe = _socket_probe()
    readyz = _http_probe(f"{base}/readyz")
    dashboard = _http_probe(f"{base}/")
    release_status = _http_probe(f"{base}/release/status")
    release_mounts = _http_probe(f"{base}/release/mounts")
    tor = _tor_files()

    checks = {
        "local_app_socket": bool(socket_probe["ok"]),
        "local_readyz_http": bool(readyz["ok"] and readyz["status_code"] == 200),
        "local_dashboard_http": bool(dashboard["ok"]),
        "release_status_http": bool(release_status["ok"]),
        "release_mounts_http": bool(release_mounts["ok"]),
    }

    # Dashboard GO is allowed when local readiness works. Tor/onion details are visible
    # but not blocking unless a future operator policy explicitly requires onion publish.
    local_runtime_ready = bool(
        checks["local_app_socket"]
        and checks["local_readyz_http"]
        and checks["local_dashboard_http"]
    )

    host_port_note = "If host browser cannot reach the app, publish 127.0.0.1:5000:5000 on the tor service when app uses network_mode: service:tor."

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "generated_at": utc_now(),
        "status": "pass" if local_runtime_ready else "needs_review",
        "decision": "GO" if local_runtime_ready else "HOLD",
        "local_base_url": base,
        "local_runtime_ready": local_runtime_ready,
        "checks": checks,
        "local": {
            "socket": socket_probe,
            "readyz": readyz,
            "dashboard": dashboard,
            "release_status": release_status,
            "release_mounts": release_mounts,
        },
        "host_port_publication": {
            "informational": True,
            "expected_dev_mapping": "127.0.0.1:5000:5000",
            "note": host_port_note,
        },
        "tor_hidden_service": tor,
        "policy": {
            "tor_file_visibility_blocks_release_status": False,
            "onion_publish_required_for_release_go": False,
            "release_status_go_requires": [
                "version manifest match",
                "required files present",
                "latest passing release gate",
                "local app readyz works",
            ],
        },
    }
