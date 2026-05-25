#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


ROOT = Path.cwd()
VERSION = "12.10.42"

SMOKE_JSON = ROOT / "release/db_migration_smoke/DB_MIGRATION_SMOKE_V12_10_38.json"
VALIDATION_JSON = ROOT / "release/approved_draft_validation/APPROVED_DRAFT_STATIC_VALIDATION_V12_10_36.json"
PROMOTED = ROOT / "migrations/versions/0018_approved_model_migration.py"

OUT_DIR = ROOT / "release/db_smoke_exact_failure"
REPORT_JSON = OUT_DIR / "DB_SMOKE_EXACT_FAILURE_LOCATOR_V12_10_42.json"
REPORT_MD = OUT_DIR / "DB_SMOKE_EXACT_FAILURE_LOCATOR_V12_10_42.md"
FULL_OUTPUT = OUT_DIR / "FAILING_UPGRADE_OUTPUT_V12_10_42.txt"
REPAIR_TARGET = OUT_DIR / "DB_SMOKE_FAILED_TABLE_REPAIR_TARGET_V12_10_42.md"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"Missing required JSON: {path}")
    return json.loads(path.read_text())


def read(path: Path) -> str:
    try:
        return path.read_text(errors="replace")
    except Exception:
        return ""


def get_upgrade_step(smoke: Dict[str, Any]) -> Dict[str, Any]:
    for step in smoke.get("steps", []):
        if step.get("step") == "upgrade_head_temp_sqlite":
            return step
    return {}


def extract_table_blocks(text: str) -> Dict[str, str]:
    blocks: Dict[str, str] = {}
    lines = text.splitlines()

    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.search(r'op\.create_table\(\s*["\']([^"\']+)["\']', line)
        if not m:
            i += 1
            continue

        table = m.group(1)
        start = i
        depth = line.count("(") - line.count(")")
        i += 1

        while i < len(lines):
            depth += lines[i].count("(") - lines[i].count(")")
            if depth <= 0:
                i += 1
                break
            i += 1

        block = "\n".join(lines[start:i])
        blocks[table] = block

    return blocks


def extract_columns_from_block(block: str) -> List[Dict[str, Any]]:
    cols = []
    for line_no, line in enumerate(block.splitlines(), 1):
        m = re.search(r'sa\.Column\(\s*["\']([^"\']+)["\']\s*,\s*(.*)', line)
        if m:
            cols.append({
                "column": m.group(1),
                "line_in_block": line_no,
                "text": line.rstrip(),
            })
    return cols


def classify_upgrade_output(output: str) -> List[Dict[str, str]]:
    low = output.lower()
    findings: List[Dict[str, str]] = []

    def add(kind: str, reason: str, repair: str) -> None:
        findings.append({"kind": kind, "reason": reason, "repair": repair})

    if "duplicate column name" in low:
        add(
            "duplicate_column_name",
            "SQLite/SQLAlchemy rejected a table with duplicate column names.",
            "Deduplicate generated columns for the failing table; keep first occurrence and comment duplicates.",
        )

    if "duplicate" in low and "column" in low:
        add(
            "duplicate_column_or_constraint",
            "Failure mentions duplicate column/constraint.",
            "Inspect failing table block for repeated column names or constraints.",
        )

    if "compileerror" in low:
        add(
            "sqlalchemy_compile_error",
            "SQLAlchemy compile failed before or during CREATE TABLE.",
            "Inspect generated SQLAlchemy types/defaults/FK expressions in failing table block.",
        )

    if "nameerror" in low or "is not defined" in low:
        add(
            "undefined_python_symbol",
            "Migration still contains an executable undefined symbol.",
            "Replace unresolved symbols with executable SQLAlchemy values and keep TODOs as comments.",
        )

    if "typeerror" in low:
        add(
            "python_type_error",
            "Migration hit a Python TypeError while building table definition.",
            "Inspect the failing table block for invalid SQLAlchemy constructor arguments.",
        )

    if "sqlite" in low and ("syntax" in low or "operationalerror" in low):
        add(
            "sqlite_operational_error",
            "SQLite rejected generated DDL.",
            "Use portable SQLAlchemy types and remove dialect-specific expressions.",
        )

    if "foreign key" in low or "foreignkey" in low:
        add(
            "foreign_key_reference_issue",
            "SQLite/FK reference may point to unavailable table or invalid target.",
            "For smoke, remove/defer FK constraints or ensure target tables are created first.",
        )

    if not findings and output.strip():
        add(
            "unclassified_upgrade_failure",
            "Upgrade failed but automatic classifier did not match a known signature.",
            "Use the full failing upgrade output and probable failing table block for manual repair.",
        )

    return findings


def infer_probable_failing_table(smoke: Dict[str, Any], approved_order: List[str]) -> Optional[str]:
    tables_after_upgrade = set(smoke.get("tables_after_upgrade", []))
    missing = smoke.get("missing_after_upgrade", [])

    # First approved table not present after failed upgrade is the likely failure point.
    for table in approved_order:
        if table not in tables_after_upgrade:
            return table

    if missing:
        return missing[0]

    return None


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    smoke = load_json(SMOKE_JSON)
    validation = load_json(VALIDATION_JSON)

    promoted_text = read(PROMOTED)
    blocks = extract_table_blocks(promoted_text)

    approved_order = validation.get("approved_tables", [])
    tables_after_upgrade = smoke.get("tables_after_upgrade", [])
    missing_after_upgrade = smoke.get("missing_after_upgrade", [])
    lingering_after_downgrade = smoke.get("lingering_after_downgrade", [])

    upgrade_step = get_upgrade_step(smoke)
    upgrade_output = upgrade_step.get("output", "")
    FULL_OUTPUT.write_text(upgrade_output)

    probable_failing_table = infer_probable_failing_table(smoke, approved_order)
    probable_block = blocks.get(probable_failing_table or "", "")

    created_approved_tables = [t for t in approved_order if t in set(tables_after_upgrade)]
    not_created_approved_tables = [t for t in approved_order if t not in set(tables_after_upgrade)]

    findings = classify_upgrade_output(upgrade_output)

    affected = []
    for table in not_created_approved_tables:
        block = blocks.get(table, "")
        affected.append({
            "table": table,
            "probable_first_failure": table == probable_failing_table,
            "column_count": len(extract_columns_from_block(block)),
            "columns": extract_columns_from_block(block),
            "block": block,
        })

    report = {
        "version": VERSION,
        "generated_at": now(),
        "schema_mutation": "none",
        "production_db_touched": smoke.get("production_db_touched"),
        "real_config_upgrade_run": smoke.get("real_config_upgrade_run"),
        "smoke_status": smoke.get("smoke_status"),
        "version_after_upgrade": smoke.get("version_after_upgrade"),
        "version_after_downgrade": smoke.get("version_after_downgrade"),
        "approved_table_count": len(approved_order),
        "created_approved_table_count": len(created_approved_tables),
        "not_created_approved_table_count": len(not_created_approved_tables),
        "missing_after_upgrade_count": len(missing_after_upgrade),
        "lingering_after_downgrade_count": len(lingering_after_downgrade),
        "created_approved_tables": created_approved_tables,
        "not_created_approved_tables": not_created_approved_tables,
        "missing_after_upgrade": missing_after_upgrade,
        "lingering_after_downgrade": lingering_after_downgrade,
        "probable_failing_table": probable_failing_table,
        "probable_failing_table_columns": extract_columns_from_block(probable_block),
        "findings": findings,
        "upgrade_step_returncode": upgrade_step.get("returncode"),
        "failing_upgrade_output_path": str(FULL_OUTPUT),
        "affected_blocks": affected,
    }

    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True))
    write_md(report)
    write_repair_target(report)

    print(json.dumps({
        "version": VERSION,
        "smoke_status": report["smoke_status"],
        "probable_failing_table": probable_failing_table,
        "created_approved_table_count": len(created_approved_tables),
        "not_created_approved_table_count": len(not_created_approved_tables),
        "finding_count": len(findings),
        "schema_mutation": "none",
        "production_db_touched": report["production_db_touched"],
        "real_config_upgrade_run": report["real_config_upgrade_run"],
        "report_json": str(REPORT_JSON),
        "report_md": str(REPORT_MD),
        "repair_target": str(REPAIR_TARGET),
        "full_output": str(FULL_OUTPUT),
    }, indent=2, sort_keys=True))

    return 0


def write_md(report: Dict[str, Any]) -> None:
    lines = [
        "# v12.10.42 DB Smoke Exact Failure Locator",
        "",
        f"- **smoke_status**: `{report['smoke_status']}`",
        "- **schema_mutation**: `none`",
        f"- **production_db_touched**: `{report['production_db_touched']}`",
        f"- **real_config_upgrade_run**: `{report['real_config_upgrade_run']}`",
        f"- **version_after_upgrade**: `{report['version_after_upgrade']}`",
        f"- **approved_table_count**: `{report['approved_table_count']}`",
        f"- **created_approved_table_count**: `{report['created_approved_table_count']}`",
        f"- **not_created_approved_table_count**: `{report['not_created_approved_table_count']}`",
        f"- **probable_failing_table**: `{report['probable_failing_table']}`",
        f"- **failing_upgrade_output_path**: `{report['failing_upgrade_output_path']}`",
        "",
        "## Findings",
        "",
    ]

    for f in report["findings"]:
        lines.append(f"- **{f['kind']}** — {f['reason']} Repair: {f['repair']}")

    lines.extend(["", "## Created approved tables before failure", ""])
    for table in report["created_approved_tables"]:
        lines.append(f"- `{table}`")

    lines.extend(["", "## Not-created approved tables", ""])
    for table in report["not_created_approved_tables"]:
        marker = " ← probable first failure" if table == report["probable_failing_table"] else ""
        lines.append(f"- `{table}`{marker}")

    lines.extend(["", "## Probable failing table columns", ""])
    for col in report["probable_failing_table_columns"]:
        lines.append(f"- `{col['column']}` — {col['text']}")

    REPORT_MD.write_text("\n".join(lines))


def write_repair_target(report: Dict[str, Any]) -> None:
    table = report["probable_failing_table"]

    lines = [
        "# v12.10.42 DB Smoke Failed Table Repair Target",
        "",
        f"- **probable_failing_table**: `{table}`",
        f"- **created_approved_table_count**: `{report['created_approved_table_count']}`",
        f"- **not_created_approved_table_count**: `{report['not_created_approved_table_count']}`",
        "",
        "## Findings",
        "",
    ]

    for f in report["findings"]:
        lines.append(f"- **{f['kind']}**: {f['repair']}")

    lines.extend([
        "",
        "## Repair constraints for v12.10.43",
        "",
        "- Patch only the failing table block unless the full output proves another issue.",
        "- Keep TODOs as comments only.",
        "- Do not run real DB upgrade.",
        "- Rerun `make report121038` and `make report121039`.",
        "",
        "## Probable failing table block",
        "",
        "```python",
    ])

    affected = next((a for a in report["affected_blocks"] if a["probable_first_failure"]), None)
    lines.append(affected["block"] if affected else "")
    lines.extend(["```", ""])

    REPAIR_TARGET.write_text("\n".join(lines))


if __name__ == "__main__":
    raise SystemExit(main())
