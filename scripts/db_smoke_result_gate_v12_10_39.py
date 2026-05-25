#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path.cwd()
VERSION = "12.10.39"

SMOKE_JSON = ROOT / "release/db_migration_smoke/DB_MIGRATION_SMOKE_V12_10_38.json"
OUT_DIR = ROOT / "release/db_smoke_gate"
GATE_JSON = OUT_DIR / "DB_SMOKE_RESULT_GATE_V12_10_39.json"
GATE_MD = OUT_DIR / "DB_SMOKE_RESULT_GATE_V12_10_39.md"
REPAIR_MD = OUT_DIR / "DB_SMOKE_REPAIR_PLAN_V12_10_39.md"
PROMOTION_READY_JSON = OUT_DIR / "PROMOTION_READY_MANIFEST_V12_10_39.json"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_smoke() -> Dict[str, Any]:
    if not SMOKE_JSON.exists():
        raise SystemExit(f"Missing v12.10.38 smoke report: {SMOKE_JSON}. Run make report121038 first.")
    return json.loads(SMOKE_JSON.read_text())


def classify_errors(errors: List[str], steps: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    findings: List[Dict[str, str]] = []

    text = "\n".join(errors + [s.get("output", "") for s in steps]).lower()

    if "syntaxerror" in text or "invalid syntax" in text:
        findings.append({
            "class": "migration_python_syntax",
            "severity": "blocker",
            "repair": "Patch the promoted migration so Alembic can import it cleanly.",
        })

    if "sqlite" in text and ("alter" in text or "constraint" in text or "jsonb" in text):
        findings.append({
            "class": "sqlite_dialect_incompatibility",
            "severity": "review",
            "repair": "Adjust migration for SQLite-safe smoke or use batch_alter_table/portable SQLAlchemy types.",
        })

    if "approved 0018 tables missing after upgrade" in text or "missing after upgrade" in text:
        findings.append({
            "class": "missing_approved_tables_after_upgrade",
            "severity": "blocker",
            "repair": "Verify op.create_table calls and table names match approved manifest exactly.",
        })

    if "still exist after downgrade" in text or "downgrade" in text and "failed" in text:
        findings.append({
            "class": "downgrade_failure_or_lingering_tables",
            "severity": "blocker",
            "repair": "Fix drop order and downgrade symmetry for 0018 approved tables.",
        })

    if "alembic_version after upgrade" in text:
        findings.append({
            "class": "alembic_version_after_upgrade_mismatch",
            "severity": "blocker",
            "repair": "Ensure revision/down_revision chain is 0017 -> 0018 and Alembic sees 0018 as head.",
        })

    if "alembic_version after downgrade" in text:
        findings.append({
            "class": "alembic_version_after_downgrade_mismatch",
            "severity": "blocker",
            "repair": "Ensure downgrade target is 0017_v12_10_schema_reconciliation and downgrade completes.",
        })

    if not findings and errors:
        findings.append({
            "class": "unclassified_db_smoke_failure",
            "severity": "review",
            "repair": "Inspect DB_MIGRATION_SMOKE_V12_10_38.md step outputs manually.",
        })

    return findings


def build_gate() -> Dict[str, Any]:
    smoke = load_smoke()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    smoke_status = smoke.get("smoke_status")
    errors = smoke.get("errors", [])
    steps = smoke.get("steps", [])
    findings = classify_errors(errors, steps)

    db_smoke_go = smoke_status == "GO"
    release_status = "PASS GO" if db_smoke_go else "HOLD"
    next_action = "prepare final release gate" if db_smoke_go else "repair 0018 migration or smoke incompatibility before release"

    gate = {
        "version": VERSION,
        "generated_at": now(),
        "source_smoke_report": str(SMOKE_JSON),
        "db_smoke_status": smoke_status,
        "db_smoke_go": db_smoke_go,
        "release_status": release_status,
        "runtime": "pass GO",
        "route_lock": "pass GO",
        "schema_lock": "DB_SMOKE_GO" if db_smoke_go else "DB_SMOKE_HOLD",
        "production_db_touched": smoke.get("production_db_touched") is True,
        "real_config_upgrade_run": smoke.get("real_config_upgrade_run") is True,
        "temp_sqlite_only": smoke.get("schema_mutation") == "temp_sqlite_only",
        "approved_table_count": smoke.get("approved_table_count"),
        "missing_after_upgrade_count": len(smoke.get("missing_after_upgrade", [])),
        "lingering_after_downgrade_count": len(smoke.get("lingering_after_downgrade", [])),
        "version_after_upgrade": smoke.get("version_after_upgrade"),
        "version_after_downgrade": smoke.get("version_after_downgrade"),
        "error_count": len(errors),
        "warning_count": len(smoke.get("warnings", [])),
        "findings": findings,
        "next_action": next_action,
    }

    if gate["production_db_touched"] or gate["real_config_upgrade_run"]:
        gate["release_status"] = "BLOCKED"
        gate["schema_lock"] = "SAFETY_BLOCK"
        gate["findings"].append({
            "class": "safety_violation",
            "severity": "blocker",
            "repair": "Investigate immediately; v12.10.38 must never touch production DB.",
        })

    GATE_JSON.write_text(json.dumps(gate, indent=2, sort_keys=True))
    write_gate_md(gate, smoke)

    if db_smoke_go:
        PROMOTION_READY_JSON.write_text(json.dumps({
            "version": VERSION,
            "generated_at": now(),
            "promotion_ready": True,
            "release_status": "PASS GO",
            "approved_table_count": smoke.get("approved_table_count"),
            "alembic_head": "0018_approved_model_migration",
            "db_smoke_report": str(SMOKE_JSON),
            "next_build": "v12.10.40 release readiness gate",
        }, indent=2, sort_keys=True))
    else:
        write_repair_plan(gate, smoke)

    return gate


def write_gate_md(gate: Dict[str, Any], smoke: Dict[str, Any]) -> None:
    lines = [
        "# v12.10.39 DB Smoke Result Gate",
        "",
        f"- **db_smoke_status**: `{gate['db_smoke_status']}`",
        f"- **release_status**: `{gate['release_status']}`",
        f"- **schema_lock**: `{gate['schema_lock']}`",
        f"- **production_db_touched**: `{gate['production_db_touched']}`",
        f"- **real_config_upgrade_run**: `{gate['real_config_upgrade_run']}`",
        f"- **temp_sqlite_only**: `{gate['temp_sqlite_only']}`",
        f"- **approved_table_count**: `{gate['approved_table_count']}`",
        f"- **missing_after_upgrade_count**: `{gate['missing_after_upgrade_count']}`",
        f"- **lingering_after_downgrade_count**: `{gate['lingering_after_downgrade_count']}`",
        f"- **version_after_upgrade**: `{gate['version_after_upgrade']}`",
        f"- **version_after_downgrade**: `{gate['version_after_downgrade']}`",
        f"- **next_action**: `{gate['next_action']}`",
        "",
        "## Findings",
        "",
    ]

    if gate["findings"]:
        for f in gate["findings"]:
            lines.append(f"- **{f['class']}** / {f['severity']}: {f['repair']}")
    else:
        lines.append("- none")

    lines.extend(["", "## v12.10.38 errors", ""])

    if smoke.get("errors"):
        for err in smoke["errors"]:
            lines.append(f"- {err}")
    else:
        lines.append("- none")

    GATE_MD.write_text("\n".join(lines))


def write_repair_plan(gate: Dict[str, Any], smoke: Dict[str, Any]) -> None:
    lines = [
        "# v12.10.39 DB Smoke Repair Plan",
        "",
        "DB smoke is not GO. Do not release and do not run a real DB upgrade.",
        "",
        "## Repair queue",
        "",
    ]

    for f in gate["findings"]:
        lines.extend([
            f"### {f['class']}",
            "",
            f"- severity: `{f['severity']}`",
            f"- repair: {f['repair']}",
            "",
        ])

    lines.extend([
        "## Safety",
        "",
        "- production_db_touched: `False` expected",
        "- real_config_upgrade_run: `False` expected",
        "- schema mutation allowed only on temp SQLite smoke DB",
        "",
        "## Next",
        "",
        "Fix the promoted 0018 migration or smoke compatibility, rerun `make report121038`, then rerun `make report121039`.",
    ])

    REPAIR_MD.write_text("\n".join(lines))


def main() -> int:
    gate = build_gate()
    print(json.dumps({
        "version": VERSION,
        "db_smoke_status": gate["db_smoke_status"],
        "release_status": gate["release_status"],
        "schema_lock": gate["schema_lock"],
        "db_smoke_go": gate["db_smoke_go"],
        "production_db_touched": gate["production_db_touched"],
        "real_config_upgrade_run": gate["real_config_upgrade_run"],
        "finding_count": len(gate["findings"]),
        "report_json": str(GATE_JSON),
        "report_md": str(GATE_MD),
        "repair_plan": str(REPAIR_MD),
        "promotion_ready_manifest": str(PROMOTION_READY_JSON),
    }, indent=2, sort_keys=True))

    return 0 if gate["db_smoke_go"] and gate["release_status"] == "PASS GO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
