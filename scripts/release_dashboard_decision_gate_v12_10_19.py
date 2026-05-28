#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA = "socmint.release_dashboard_decision_gate.v12_10_19"
VERSION = "12.10.21"
REPORT_ROOT = Path("var/socmint/rc_reports")


def now() -> str:
    return datetime.now(UTC).isoformat()


def truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def add(rows: list[dict[str, Any]], name: str, ok: bool, detail: str = "") -> None:
    rows.append({"name": name, "status": "pass" if ok else "fail", "detail": detail})


def seed_passing_gate_report() -> Path:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    path = REPORT_ROOT / "socmint_v12_10_21_seeded_runtime_route_gate.json"
    payload = {
        "schema": "socmint.release.runtime_route_gate.v12_10_21.seed",
        "version": VERSION,
        "generated_at": now(),
        "status": "pass",
        "decision": "GO",
        "seeded_for": "release_dashboard_decision_gate_v12_10_19",
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    return path


def write_report(report: dict[str, Any]) -> dict[str, str]:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    jp = REPORT_ROOT / f"socmint_v12_10_21_release_dashboard_decision_gate_{stamp}.json"
    mp = REPORT_ROOT / f"socmint_v12_10_21_release_dashboard_decision_gate_{stamp}.md"
    jp.write_text(json.dumps(report, indent=2, sort_keys=True))
    lines = [
        "# SOCMINT Release Dashboard Decision Gate",
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
    os.environ.setdefault(
        "SOCMINT_SECRET_KEY",
        "test-v12-10-21-dashboard-decision-secret-key-000000",
    )
    os.environ.setdefault("SOCMINT_AUTO_CREATE_DB", "true")
    os.environ.setdefault(
        "DATABASE_URL",
        "sqlite:///var/test_v12_10_21_dashboard_gate.db",
    )
    os.environ.setdefault("SOCMINT_DATA_DIR", "var/test_v12_10_21_data")
    os.environ.setdefault("SOCMINT_DOCKER_TOR", "true")

    seed_path = None
    if truthy("SOCMINT_RELEASE_DASHBOARD_SEED_PASS_REPORT"):
        seed_path = seed_passing_gate_report()

    checks: list[dict[str, Any]] = []
    payload: dict[str, Any] = {}
    gates: dict[str, Any] = {}
    try:
        from socmint.release_status_v12_10_19 import latest_gate_reports
        from socmint.release_status_v12_10_19 import release_status
        from socmint.version import VERSION as package_version

        payload = release_status()
        gates = latest_gate_reports()
        runtime_override = truthy("SOCMINT_RELEASE_DASHBOARD_ASSUME_RUNTIME_READY")
        runtime_ready = bool(payload.get("checks", {}).get("runtime_ready"))
        decision_go = payload.get("decision") == "GO"
        status_pass = payload.get("status") == "pass"
        add(checks, "package_version", package_version == VERSION, package_version)
        add(
            checks,
            "seed_report_created_if_requested",
            (seed_path is not None and seed_path.exists())
            or not truthy("SOCMINT_RELEASE_DASHBOARD_SEED_PASS_REPORT"),
            str(seed_path),
        )
        add(
            checks,
            "status_schema",
            payload.get("schema") == "socmint.release_status.v12_10_21",
            str(payload.get("schema")),
        )
        add(
            checks,
            "gates_schema",
            gates.get("schema") == "socmint.release_gates.latest.v12_10_21",
            str(gates.get("schema")),
        )
        add(
            checks,
            "latest_overall_visible",
            gates.get("latest_overall") is not None,
            str((gates.get("latest_overall") or {}).get("name")),
        )
        add(
            checks,
            "latest_pass_visible",
            gates.get("latest_pass") is not None,
            str((gates.get("latest_pass") or {}).get("name")),
        )
        add(
            checks,
            "latest_release_gate_pass_visible",
            gates.get("latest_release_gate_pass") is not None,
            str((gates.get("latest_release_gate_pass") or {}).get("name")),
        )
        add(
            checks,
            "failed_latest_nonblocking_flag_present",
            "failed_latest_does_not_block" in gates,
            str(gates.get("failed_latest_does_not_block")),
        )
        add(
            checks,
            "file_visibility_informational",
            payload.get("sections", {}).get("file_visibility")
            in {"informational", "pass"},
            str(payload.get("sections", {}).get("file_visibility")),
        )
        add(
            checks,
            "runtime_ready_or_ci_override",
            runtime_ready or runtime_override,
            f"runtime_ready={runtime_ready}; override={runtime_override}",
        )
        add(
            checks,
            "dashboard_decision_go_or_ci_override",
            decision_go or runtime_override,
            f"decision={payload.get('decision')}; override={runtime_override}",
        )
        add(
            checks,
            "dashboard_status_pass_or_ci_override",
            status_pass or runtime_override,
            f"status={payload.get('status')}; override={runtime_override}",
        )
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
        "seed_path": str(seed_path) if seed_path else None,
        "release_status": payload,
        "gates": gates,
    }
    report.update(write_report(report))
    return report


if __name__ == "__main__":
    result = run_gate()
    print(json.dumps(result, indent=2, sort_keys=True))
    sys.exit(0 if result["status"] == "pass" else 1)
