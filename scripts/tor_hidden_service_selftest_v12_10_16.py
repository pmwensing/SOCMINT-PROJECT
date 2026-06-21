#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA = "socmint.tor_topology_selftest.v12_10_16"
VERSION = "12.10.16"
REPORT_ROOT = Path("var/socmint/rc_reports")


def now() -> str:
    return datetime.now(UTC).isoformat()


def cmd(args: list[str], timeout: int = 30) -> dict[str, Any]:
    try:
        p = subprocess.run(
            args, text=True, capture_output=True, timeout=timeout, check=False
        )
        return {
            "args": args,
            "ok": p.returncode == 0,
            "returncode": p.returncode,
            "stdout": p.stdout,
            "stderr": p.stderr,
        }
    except Exception as exc:
        return {
            "args": args,
            "ok": False,
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
        }


def check(rows: list[dict[str, Any]], name: str, ok: bool, detail: str = "") -> None:
    rows.append({"name": name, "status": "pass" if ok else "fail", "detail": detail})


def write_report(report: dict[str, Any]) -> dict[str, str]:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    jp = REPORT_ROOT / f"socmint_v12_10_16_tor_topology_selftest_{stamp}.json"
    mp = REPORT_ROOT / f"socmint_v12_10_16_tor_topology_selftest_{stamp}.md"
    jp.write_text(json.dumps(report, indent=2, sort_keys=True))
    lines = [
        "# SOCMINT v12.10.16 Tor Topology Self-Test",
        "",
        f"- Status: `{report['status']}`",
        f"- Decision: `{report['decision']}`",
        "",
        "## Checks",
        "",
    ]
    for row in report["checks"]:
        lines.append(f"- `{row['status']}` — {row['name']} — {row.get('detail', '')}")
    lines.extend(["", "## Finding", "", report["finding"], ""])
    mp.write_text("\n".join(lines))
    return {"json_path": str(jp), "markdown_path": str(mp)}


def main() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    compose = cmd(["docker", "compose", "config"])
    text = compose["stdout"]
    check(checks, "compose_config", compose["ok"], "docker compose config")
    check(
        checks,
        "app_network_mode_service_tor",
        "network_mode: service:tor" in text,
        "app shares tor network namespace",
    )
    check(
        checks,
        "app_binds_local_5000",
        "127.0.0.1:5000" in text,
        "app health/gunicorn target is local 5000",
    )
    check(
        checks,
        "torrc_bind_mount",
        "deploy/tor/torrc" in text and "/etc/tor/torrc" in text,
        "source torrc is mounted into tor container",
    )

    torrc_path = Path("deploy/tor/torrc")
    torrc = torrc_path.read_text() if torrc_path.exists() else ""
    check(checks, "source_torrc_present", torrc_path.exists(), str(torrc_path))
    check(
        checks,
        "hidden_service_port_mapping",
        "HiddenServicePort 80 127.0.0.1:5000" in torrc,
        "expected local target mapping",
    )

    ready = cmd(
        [
            "docker",
            "compose",
            "exec",
            "-T",
            "app",
            "python3",
            "-c",
            "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:5000/readyz', timeout=5).read().decode())",
        ]
    )
    check(
        checks,
        "app_readyz",
        ready["ok"] and "ready" in ready["stdout"],
        "app readyz works inside shared namespace",
    )

    api = cmd(
        [
            "docker",
            "compose",
            "exec",
            "-T",
            "app",
            "python3",
            "-c",
            "from src.socmint.tor_production import tor_hidden_service_diagnostics; import json; print(json.dumps(tor_hidden_service_diagnostics(), sort_keys=True))",
        ]
    )
    payload = {}
    if api["ok"]:
        try:
            payload = json.loads(api["stdout"].strip().splitlines()[-1])
        except Exception:
            payload = {}
    check(
        checks,
        "api_payload_schema",
        payload.get("schema") == "socmint.tor_hidden_service_diagnostics.v12_10_16",
        str(payload.get("schema")),
    )
    check(
        checks,
        "api_payload_status",
        payload.get("status") == "pass",
        str(payload.get("status")),
    )

    failed = [r for r in checks if r["status"] != "pass"]
    report = {
        "schema": SCHEMA,
        "version": VERSION,
        "generated_at": now(),
        "status": "pass" if not failed else "fail",
        "decision": "GO" if not failed else "HOLD",
        "checks": checks,
        "finding": "The local 127.0.0.1:5000 target is correct when app uses network_mode: service:tor and gunicorn binds to 127.0.0.1:5000.",
        "compose_config": compose,
        "torrc_text": torrc,
        "readyz": ready,
        "api_diagnostics": payload,
    }
    report.update(write_report(report))
    return report


if __name__ == "__main__":
    result = main()
    print(json.dumps(result, indent=2, sort_keys=True))
    sys.exit(0 if result["status"] == "pass" else 1)
