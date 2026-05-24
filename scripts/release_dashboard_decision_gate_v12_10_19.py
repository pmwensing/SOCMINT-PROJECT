#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA = "socmint.release_dashboard_decision_gate.v12_10_19"
VERSION = "12.10.19"
REPORT_ROOT = Path("var/socmint/rc_reports")


def now() -> str:
    return datetime.now(UTC).isoformat()


def add(rows: list[dict[str, Any]], name: str, ok: bool, detail: str = "") -> None:
    rows.append({"name": name, "status": "pass" if ok else "fail", "detail": detail})


def write_report(report: dict[str, Any]) -> dict[str, str]:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    jp = REPORT_ROOT / f"socmint_v12_10_19_release_dashboard_decision_gate_{stamp}.json"
    mp = REPORT_ROOT / f"socmint_v12_10_19_release_dashboard_decision_gate_{stamp}.md"
    jp.write_text(json.dumps(report, indent=2, sort_keys=True))
    lines = [
        "# SOCMINT v12.10.19 Release Dashboard Decision Gate",
        "",
        f"- Status: `{report['status']}`",
        f"- Decision: `{report['decision']}`",
        "",
        "## Checks",
        "",
    ]
    for row in report["checks"]:
        lines.append(f"- `{row['status']}` — {row['name']} — {row.get('detail', '')}")
    mp.write_text("\n".join(lines) + "\n")
    return {"json_path": str(jp), "markdown_path": str(mp)}


def run_gate() -> dict[str, Any]:
    os.environ.setdefault("SOCMINT_SECRET_KEY", "test-v12-10-19-dashboard-decision-secret-key-000000")
    os.environ.setdefault("SOCMINT_AUTO_CREATE_DB", "true")
    os.environ.setdefault("DATABASE_URL", "sqlite:///var/test_v12_10_19_dashboard_gate.db")
    os.environ.setdefault("SOCMINT_DATA_DIR", "var/test_v12_10_19_data")
    os.environ.setdefault("SOCMINT_DOCKER_TOR", "true")

    checks: list[dict[str, Any]] = []
    payload: dict[str, Any] = {}
    gates: dict[str, Any] = {}
    try:
        from socmint.version import VERSION as package_version
        from socmint.release_status_v12_10_19 import release_status, latest_gate_reports
        payload = release_status()
        gates = latest_gate_reports()
        add(checks, "package_version", package_version == VERSION, package_version)
        add(checks, "status_schema", payload.get("schema") == "socmint.release_status.v12_10_19", str(payload.get("schema")))
        add(checks, "gates_schema", gates.get("schema") == "socmint.release_gates.latest.v12_10_19", str(gates.get("schema")))
        add(checks, "latest_overall_visible", gates.get("latest_overall") is not None, str((gates.get("latest_overall") or {}).get("name")))
        add(checks, "latest_pass_visible", gates.get("latest_pass") is not None, str((gates.get("latest_pass") or {}).get("name")))
        add(checks, "latest_release_gate_pass_visible", gates.get("latest_release_gate_pass") is not None, str((gates.get("latest_release_gate_pass") or {}).get("name")))
        add(checks, "failed_latest_nonblocking_flag_present", "failed_latest_does_not_block" in gates, str(gates.get("failed_latest_does_not_block")))
        add(checks, "tor_file_visibility_informational", payload.get("sections", {}).get("file_visibility") in {"informational", "pass"}, str(payload.get("sections", {}).get("file_visibility")))
        add(checks, "runtime_ready", bool(payload.get("checks", {}).get("runtime_ready")), str(payload.get("checks", {}).get("runtime_ready")))
        add(checks, "dashboard_decision_go", payload.get("decision") == "GO", str(payload.get("decision")))
        add(checks, "dashboard_status_pass", payload.get("status") == "pass", str(payload.get("status")))
    except Exception as exc:
        add(checks, "decision_engine_import_and_run", False, repr(exc))

    failed = [row for row in checks if row["status"] != "pass"]
    report = {
        "schema": SCHEMA,
        "version": VERSION,
        "generated_at": now(),
        "status": "pass" if not failed else "fail",
        "decision": "GO" if not failed else "HOLD",
        "checks": checks,
        "release_status": payload,
        "gates": gates,
    }
    report.update(write_report(report))
    return report


if __name__ == "__main__":
    result = run_gate()
    print(json.dumps(result, indent=2, sort_keys=True))
    sys.exit(0 if result["status"] == "pass" else 1)
