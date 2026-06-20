#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA = "socmint.release.subject_to_dossier_e2e.v12_10_14"
VERSION = "12.10.14"


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def pii_hash(value: str) -> str:
    return hashlib.sha256(value.strip().lower().encode("utf-8")).hexdigest()


def check_file(path: str | None) -> dict[str, Any]:
    if not path:
        return {"path": path, "exists": False, "size_bytes": 0}
    p = Path(path)
    return {
        "path": str(p),
        "exists": p.exists(),
        "size_bytes": p.stat().st_size if p.exists() else 0,
    }


def write_report(
    report: dict[str, Any], root: str = "var/socmint/rc_reports"
) -> dict[str, str]:
    out = Path(root)
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    json_path = out / f"socmint_v12_10_14_subject_to_dossier_e2e_{stamp}.json"
    md_path = out / f"socmint_v12_10_14_subject_to_dossier_e2e_{stamp}.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True))
    lines = [
        "# SOCMINT v12.10.14 Subject-to-Dossier E2E Gate",
        "",
        f"- Schema: `{report['schema']}`",
        f"- Version: `{report['version']}`",
        f"- Generated: `{report['generated_at']}`",
        f"- Status: `{report['status']}`",
        f"- Decision: `{report['decision']}`",
        f"- Subject ID: `{report.get('subject_id')}`",
        "",
        "## Checks",
        "",
    ]
    for row in report.get("checks", []):
        lines.append(f"- `{row['status']}` — {row['name']} — {row.get('detail', '')}")
    if report.get("error"):
        lines.extend(["", "## Error", "", f"```text\n{report['error']}\n```"])
    md_path.write_text("\n".join(lines) + "\n")
    return {"json_path": str(json_path), "markdown_path": str(md_path)}


def add_check(
    checks: list[dict[str, Any]], name: str, ok: bool, detail: str = ""
) -> None:
    checks.append({"name": name, "status": "pass" if ok else "fail", "detail": detail})


def run_gate() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    try:
        from socmint import database as db
        from socmint.command_center import command_center_payload
        from socmint.entity_dossier_v2 import export_full_entity_dossier_v2
        from socmint.rc_regression_gate_v12_10 import write_rc_report
        from socmint.version import VERSION as package_version

        add_check(
            checks, "package_version", package_version == VERSION, package_version
        )

        db.ensure_configured()
        add_check(
            checks, "database_configured", db.Session is not None, "Session available"
        )

        subject_id = db.create_spine_subject("v12.10.14 RC E2E Subject")
        add_check(
            checks, "create_subject", bool(subject_id), f"subject_id={subject_id}"
        )

        seed_value = "analyst-v12-10-14@example.test"
        seed_id = db.add_spine_seed(
            subject_id=subject_id,
            seed_type="email",
            raw_value=seed_value,
            normalized_value=seed_value.lower(),
            pii_hash=pii_hash(seed_value),
        )
        add_check(checks, "add_seed", bool(seed_id), f"seed_id={seed_id}")

        run_id = db.create_spine_connector_run(
            subject_id=subject_id,
            connector_key="release_gate.synthetic",
            seed_id=seed_id,
            status="completed",
            raw_result={
                "schema": "socmint.release.synthetic_connector_result.v12_10_14",
                "status": "completed",
                "findings": [
                    {
                        "type": "email",
                        "value": seed_value.lower(),
                        "confidence": 0.99,
                        "source": "release_gate",
                    }
                ],
            },
        )
        add_check(checks, "create_connector_run", bool(run_id), f"run_id={run_id}")

        observation_id = db.create_spine_observation(
            subject_id=subject_id,
            run_id=run_id,
            observation_type="email_account_signal",
            normalized_value=seed_value.lower(),
            confidence="0.99",
            source_ref="release_gate.synthetic",
            evidence_ref=f"spine_connector_run:{run_id}",
            payload={
                "schema": "socmint.release.synthetic_observation.v12_10_14",
                "diagnostic": False,
                "seed_id": seed_id,
            },
        )
        add_check(
            checks,
            "create_observation",
            bool(observation_id),
            f"observation_id={observation_id}",
        )

        assertion_id = db.upsert_spine_assertion(
            subject_id=subject_id,
            assertion_type="email_identity",
            normalized_value=seed_value.lower(),
            confidence="0.99",
            validation_state="unreviewed",
            payload={
                "schema": "socmint.release.synthetic_assertion.v12_10_14",
                "observation_id": observation_id,
                "evidence_ref": f"spine_observation:{observation_id}",
            },
        )
        add_check(
            checks,
            "create_assertion",
            bool(assertion_id),
            f"assertion_id={assertion_id}",
        )

        confirmed_id = db.validate_spine_assertion(
            assertion_id,
            actor="release_gate",
            action="confirmed",
            note="v12.10.14 approve path",
        )
        confirmed = db.get_spine_assertion(assertion_id)
        add_check(
            checks,
            "approve_assertion",
            bool(
                confirmed_id and confirmed and confirmed.validation_state == "confirmed"
            ),
            getattr(confirmed, "validation_state", "missing"),
        )

        rejected_id = db.validate_spine_assertion(
            assertion_id,
            actor="release_gate",
            action="rejected",
            note="v12.10.14 reject path",
        )
        rejected = db.get_spine_assertion(assertion_id)
        add_check(
            checks,
            "reject_assertion",
            bool(rejected_id and rejected and rejected.validation_state == "rejected"),
            getattr(rejected, "validation_state", "missing"),
        )

        command = command_center_payload()
        add_check(
            checks,
            "command_center_payload",
            command.get("schema") == "socmint.command_center.v12_9_1",
            str(command.get("schema")),
        )

        export = export_full_entity_dossier_v2(subject_id)
        json_file = check_file(export.get("json_path"))
        html_file = check_file(export.get("html_path"))
        add_check(
            checks,
            "dossier_json_export",
            json_file["exists"] and json_file["size_bytes"] > 0,
            json_file["path"],
        )
        add_check(
            checks,
            "dossier_html_export",
            html_file["exists"] and html_file["size_bytes"] > 0,
            html_file["path"],
        )

        rc = write_rc_report(root="var/socmint/rc_reports")
        rc_json = check_file(rc.get("json_path"))
        rc_md = check_file(rc.get("markdown_path"))
        add_check(
            checks,
            "rc_report_json",
            rc_json["exists"] and rc_json["size_bytes"] > 0,
            rc_json["path"],
        )
        add_check(
            checks,
            "rc_report_markdown",
            rc_md["exists"] and rc_md["size_bytes"] > 0,
            rc_md["path"],
        )

        failed = [row for row in checks if row["status"] != "pass"]
        report = {
            "schema": SCHEMA,
            "version": VERSION,
            "generated_at": utc_now(),
            "status": "pass" if not failed else "fail",
            "decision": "GO" if not failed else "FAIL",
            "subject_id": subject_id,
            "seed_id": seed_id,
            "run_id": run_id,
            "observation_id": observation_id,
            "assertion_id": assertion_id,
            "checks": checks,
            "dossier_export": export,
            "rc_export": rc,
        }
    except Exception as exc:
        report = {
            "schema": SCHEMA,
            "version": VERSION,
            "generated_at": utc_now(),
            "status": "fail",
            "decision": "FAIL",
            "error": str(exc),
            "checks": checks,
        }
    report.update(write_report(report))
    return report


if __name__ == "__main__":
    result = run_gate()
    print(json.dumps(result, indent=2, sort_keys=True))
    sys.exit(0 if result.get("status") == "pass" else 1)
