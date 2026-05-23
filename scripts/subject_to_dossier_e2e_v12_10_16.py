#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA = "socmint.release.subject_to_dossier_e2e.v12_10_16"
VERSION = "12.10.16"


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def pii_hash(value: str) -> str:
    return hashlib.sha256(value.strip().lower().encode("utf-8")).hexdigest()


def file_ok(path: str | None) -> bool:
    return bool(path and Path(path).exists() and Path(path).stat().st_size > 0)


def write_report(report: dict[str, Any], root: str = "var/socmint/rc_reports") -> dict[str, str]:
    out = Path(root)
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    jp = out / f"socmint_v12_10_16_subject_to_dossier_e2e_{stamp}.json"
    mp = out / f"socmint_v12_10_16_subject_to_dossier_e2e_{stamp}.md"
    jp.write_text(json.dumps(report, indent=2, sort_keys=True))
    lines = ["# SOCMINT v12.10.16 Subject-to-Dossier E2E Gate", "", f"- Status: `{report['status']}`", f"- Decision: `{report['decision']}`", "", "## Checks", ""]
    for row in report.get("checks", []):
        lines.append(f"- `{row['status']}` — {row['name']} — {row.get('detail', '')}")
    mp.write_text("\n".join(lines) + "\n")
    return {"json_path": str(jp), "markdown_path": str(mp)}


def add(checks: list[dict[str, Any]], name: str, ok: bool, detail: str = "") -> None:
    checks.append({"name": name, "status": "pass" if ok else "fail", "detail": detail})


def run_gate() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    try:
        from socmint import database as db
        from socmint.command_center import command_center_payload
        from socmint.entity_dossier_v2 import export_full_entity_dossier_v2
        from socmint.rc_regression_gate_v12_10 import write_rc_report
        from socmint.tor_production import tor_hidden_service_diagnostics
        from socmint.version import VERSION as package_version

        add(checks, "package_version", package_version == VERSION, package_version)
        db.ensure_configured()
        add(checks, "database_configured", db.Session is not None, "Session available")
        subject_id = db.create_spine_subject("v12.10.16 Tor Diagnostics E2E Subject")
        add(checks, "create_subject", bool(subject_id), f"subject_id={subject_id}")
        seed_value = "analyst-v12-10-16@example.test"
        seed_id = db.add_spine_seed(subject_id, "email", seed_value, seed_value.lower(), pii_hash(seed_value))
        add(checks, "add_seed", bool(seed_id), f"seed_id={seed_id}")
        run_id = db.create_spine_connector_run(subject_id, "release_gate.synthetic", seed_id, "completed", {"schema": "socmint.release.synthetic_connector_result.v12_10_16", "status": "completed"})
        add(checks, "create_connector_run", bool(run_id), f"run_id={run_id}")
        obs_id = db.create_spine_observation(subject_id, run_id, "email_account_signal", seed_value.lower(), "0.99", "release_gate.synthetic", f"spine_connector_run:{run_id}", {"schema": "socmint.release.synthetic_observation.v12_10_16", "diagnostic": False})
        add(checks, "create_observation", bool(obs_id), f"observation_id={obs_id}")
        assertion_id = db.upsert_spine_assertion(subject_id, "email_identity", seed_value.lower(), "0.99", "unreviewed", {"schema": "socmint.release.synthetic_assertion.v12_10_16", "observation_id": obs_id})
        add(checks, "create_assertion", bool(assertion_id), f"assertion_id={assertion_id}")
        db.validate_spine_assertion(assertion_id, "release_gate", "confirmed", "v12.10.16 approve path")
        add(checks, "approve_assertion", db.get_spine_assertion(assertion_id).validation_state == "confirmed", "confirmed")
        db.validate_spine_assertion(assertion_id, "release_gate", "rejected", "v12.10.16 reject path")
        add(checks, "reject_assertion", db.get_spine_assertion(assertion_id).validation_state == "rejected", "rejected")
        command = command_center_payload()
        add(checks, "command_center_payload", command.get("schema") == "socmint.command_center.v12_9_1", str(command.get("schema")))
        tor_diag = tor_hidden_service_diagnostics()
        add(checks, "tor_diagnostics_payload", tor_diag.get("schema") == "socmint.tor_hidden_service_diagnostics.v12_10_16", str(tor_diag.get("schema")))
        export = export_full_entity_dossier_v2(subject_id)
        add(checks, "dossier_json_export", file_ok(export.get("json_path")), str(export.get("json_path")))
        add(checks, "dossier_html_export", file_ok(export.get("html_path")), str(export.get("html_path")))
        rc = write_rc_report(root="var/socmint/rc_reports")
        add(checks, "rc_report_json", file_ok(rc.get("json_path")), str(rc.get("json_path")))
        add(checks, "rc_report_markdown", file_ok(rc.get("markdown_path")), str(rc.get("markdown_path")))
        failed = [row for row in checks if row["status"] != "pass"]
        report = {"schema": SCHEMA, "version": VERSION, "generated_at": utc_now(), "status": "pass" if not failed else "fail", "decision": "GO" if not failed else "FAIL", "subject_id": subject_id, "checks": checks, "dossier_export": export, "rc_export": rc}
    except Exception as exc:
        report = {"schema": SCHEMA, "version": VERSION, "generated_at": utc_now(), "status": "fail", "decision": "FAIL", "error": str(exc), "checks": checks}
    report.update(write_report(report))
    return report


if __name__ == "__main__":
    result = run_gate()
    print(json.dumps(result, indent=2, sort_keys=True))
    sys.exit(0 if result.get("status") == "pass" else 1)
