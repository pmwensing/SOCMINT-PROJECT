#!/usr/bin/env python3
from __future__ import annotations

import configparser
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


ROOT = Path.cwd()
VERSION = "12.10.45A"

SMOKE_JSON = ROOT / "release/db_migration_smoke/DB_MIGRATION_SMOKE_V12_10_38.json"
VALIDATION_JSON = ROOT / "release/approved_draft_validation/APPROVED_DRAFT_STATIC_VALIDATION_V12_10_36.json"
LOCATOR_JSON = ROOT / "release/db_smoke_exact_failure/DB_SMOKE_EXACT_FAILURE_LOCATOR_V12_10_42.json"

OUT_DIR = ROOT / "release/missing_table_block_detector"
REPORT_JSON = OUT_DIR / "MISSING_TABLE_BLOCK_DETECTOR_V12_10_45A.json"
REPORT_MD = OUT_DIR / "MISSING_TABLE_BLOCK_DETECTOR_V12_10_45A.md"
REPAIR_PLAN = OUT_DIR / "MISSING_TABLE_BLOCK_REPAIR_PLAN_V12_10_45A.md"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(cmd: List[str]) -> Tuple[int, str]:
    try:
        out = subprocess.check_output(cmd, cwd=ROOT, stderr=subprocess.STDOUT, text=True)
        return 0, out
    except subprocess.CalledProcessError as exc:
        return exc.returncode, exc.output


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def active_migration() -> Path:
    cfg = configparser.ConfigParser()
    cfg.read(ROOT / "alembic.ini")
    script_location = cfg.get("alembic", "script_location", fallback="migrations")
    return ROOT / script_location / "versions" / "0018_approved_model_migration.py"


def extract_create_tables(text: str) -> List[str]:
    return re.findall(r'op\.create_table\(\s*["\']([^"\']+)["\']', text)


def extract_drop_tables(text: str) -> List[str]:
    return re.findall(r'op\.drop_table\(\s*["\']([^"\']+)["\']', text)


def find_create_block(text: str, table: str) -> str:
    lines = text.splitlines()
    start = -1

    for idx, line in enumerate(lines):
        if re.search(r'op\.create_table\(\s*["\']' + re.escape(table) + r'["\']', line):
            start = idx
            break

    if start < 0:
        return ""

    depth = 0
    seen = False
    end = start

    for idx in range(start, len(lines)):
        depth += lines[idx].count("(")
        depth -= lines[idx].count(")")
        if "(" in lines[idx]:
            seen = True
        end = idx
        if seen and depth <= 0:
            break

    return "\n".join(lines[start:end + 1])


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    smoke = load_json(SMOKE_JSON)
    validation = load_json(VALIDATION_JSON)
    locator = load_json(LOCATOR_JSON)

    migration_path = active_migration()
    if not migration_path.exists():
        raise SystemExit(f"Missing promoted migration: {migration_path}")

    text = migration_path.read_text()

    approved_tables = validation.get("approved_tables", []) or smoke.get("approved_tables", [])
    create_tables = extract_create_tables(text)
    drop_tables = extract_drop_tables(text)

    approved_set = set(approved_tables)
    create_set = set(create_tables)
    drop_set = set(drop_tables)

    missing_create_blocks = sorted(approved_set - create_set)
    extra_create_blocks = sorted(create_set - approved_set)
    missing_drop_blocks = sorted(approved_set - drop_set)
    extra_drop_blocks = sorted(drop_set - approved_set)

    smoke_missing_after_upgrade = smoke.get("missing_after_upgrade", [])
    tables_after_upgrade = set(smoke.get("tables_after_upgrade", []))

    # Tables that were never created because the migration file has no create block.
    structural_missing = sorted(set(missing_create_blocks))

    # Tables that have blocks but were not created, so they are likely after the failing operation.
    blocked_by_failure = sorted([
        t for t in smoke_missing_after_upgrade
        if t in create_set and t not in tables_after_upgrade
    ])

    probable_from_locator = locator.get("probable_failing_table")

    if probable_from_locator in structural_missing:
        corrected_failure_class = "missing_create_table_block"
    elif probable_from_locator in create_set:
        corrected_failure_class = "create_table_block_exists_but_upgrade_failed_before_or_at_table"
    else:
        corrected_failure_class = "locator_probable_table_not_approved_or_not_in_migration"

    py_code, py_out = run(["python", "-m", "py_compile", str(migration_path)])
    heads_code, heads_out = run(["alembic", "heads"])

    errors = []
    if py_code != 0:
        errors.append("promoted migration does not compile")
    if heads_code != 0:
        errors.append("alembic heads failed")
    if "0018_approved_model_migration" not in heads_out:
        errors.append("alembic does not see 0018 head")

    report = {
        "version": VERSION,
        "generated_at": now(),
        "schema_mutation": "none",
        "production_db_touched": False,
        "real_config_upgrade_run": False,
        "promoted_migration": str(migration_path),
        "approved_table_count": len(approved_tables),
        "create_table_count": len(create_tables),
        "drop_table_count": len(drop_tables),
        "approved_tables": approved_tables,
        "create_tables": create_tables,
        "drop_tables": drop_tables,
        "missing_create_blocks": missing_create_blocks,
        "extra_create_blocks": extra_create_blocks,
        "missing_drop_blocks": missing_drop_blocks,
        "extra_drop_blocks": extra_drop_blocks,
        "smoke_missing_after_upgrade": smoke_missing_after_upgrade,
        "structural_missing": structural_missing,
        "blocked_by_failure": blocked_by_failure,
        "probable_from_locator": probable_from_locator,
        "corrected_failure_class": corrected_failure_class,
        "missing_structural_blocks": [
            {
                "table": table,
                "approved": table in approved_set,
                "create_block": find_create_block(text, table),
            }
            for table in structural_missing
        ],
        "compile": {"returncode": py_code, "output": py_out},
        "alembic_heads": {"returncode": heads_code, "output": heads_out},
        "errors": errors,
        "detector_status": "GO" if not errors else "NO-GO",
        "next_action": "build v12.10.45B missing create/drop block generator from approved candidate metadata"
        if structural_missing else "repair existing failing table block with v12.10.43-style targeted patch",
    }

    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True))
    write_md(report)
    write_plan(report)

    print(json.dumps({
        "version": VERSION,
        "detector_status": report["detector_status"],
        "approved_table_count": len(approved_tables),
        "create_table_count": len(create_tables),
        "drop_table_count": len(drop_tables),
        "missing_create_block_count": len(missing_create_blocks),
        "missing_drop_block_count": len(missing_drop_blocks),
        "structural_missing": structural_missing,
        "blocked_by_failure": blocked_by_failure,
        "probable_from_locator": probable_from_locator,
        "corrected_failure_class": corrected_failure_class,
        "schema_mutation": "none",
        "production_db_touched": False,
        "real_config_upgrade_run": False,
        "report_json": str(REPORT_JSON),
        "report_md": str(REPORT_MD),
        "repair_plan": str(REPAIR_PLAN),
    }, indent=2, sort_keys=True))

    return 0 if not errors else 1


def write_md(report: Dict[str, Any]) -> None:
    lines = [
        "# v12.10.45A Missing Table Block Detector",
        "",
        f"- **detector_status**: `{report['detector_status']}`",
        "- **schema_mutation**: `none`",
        "- **production_db_touched**: `False`",
        "- **real_config_upgrade_run**: `False`",
        f"- **approved_table_count**: `{report['approved_table_count']}`",
        f"- **create_table_count**: `{report['create_table_count']}`",
        f"- **drop_table_count**: `{report['drop_table_count']}`",
        f"- **missing_create_blocks**: `{len(report['missing_create_blocks'])}`",
        f"- **missing_drop_blocks**: `{len(report['missing_drop_blocks'])}`",
        f"- **probable_from_locator**: `{report['probable_from_locator']}`",
        f"- **corrected_failure_class**: `{report['corrected_failure_class']}`",
        f"- **next_action**: `{report['next_action']}`",
        "",
        "## Missing create blocks",
        "",
    ]

    if report["missing_create_blocks"]:
        for table in report["missing_create_blocks"]:
            lines.append(f"- `{table}`")
    else:
        lines.append("- none")

    lines.extend(["", "## Missing drop blocks", ""])

    if report["missing_drop_blocks"]:
        for table in report["missing_drop_blocks"]:
            lines.append(f"- `{table}`")
    else:
        lines.append("- none")

    lines.extend(["", "## Blocked by failure but create block exists", ""])

    if report["blocked_by_failure"]:
        for table in report["blocked_by_failure"]:
            lines.append(f"- `{table}`")
    else:
        lines.append("- none")

    lines.extend(["", "## Errors", ""])

    if report["errors"]:
        for err in report["errors"]:
            lines.append(f"- {err}")
    else:
        lines.append("- none")

    REPORT_MD.write_text("\n".join(lines))


def write_plan(report: Dict[str, Any]) -> None:
    lines = [
        "# v12.10.45A Missing Table Block Repair Plan",
        "",
        "Do not patch a nonexistent create_table block.",
        "",
        "## Structural missing approved tables",
        "",
    ]

    if report["structural_missing"]:
        for table in report["structural_missing"]:
            lines.append(f"- `{table}`")
    else:
        lines.append("- none")

    lines.extend([
        "",
        "## v12.10.45B plan",
        "",
        "If structural missing tables exist:",
        "",
        "1. Read v12.10.33 candidate JSON for the missing tables.",
        "2. Reconstruct create_table blocks from approved extracted column hints.",
        "3. Insert missing create_table blocks into upgrade in approved-table order.",
        "4. Insert missing drop_table calls into downgrade reverse order.",
        "5. Validate static symmetry.",
        "6. Rerun temp SQLite smoke.",
        "7. Do not run real DB upgrade.",
        "",
        "If no structural missing tables exist:",
        "",
        "- Use the v12.10.42 failed table repair target and patch the existing block.",
    ])

    REPAIR_PLAN.write_text("\n".join(lines))


if __name__ == "__main__":
    raise SystemExit(main())
