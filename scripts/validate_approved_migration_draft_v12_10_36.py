#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path.cwd()
VERSION = "12.10.36"

DRAFT = ROOT / "release/approved_migration_draft/0018_APPROVED_MODEL_MIGRATION_DRAFT_V12_10_35.py"
MANIFEST = ROOT / "release/approved_migration_draft/APPROVED_MIGRATION_DRAFT_MANIFEST_V12_10_35.json"
OUT_DIR = ROOT / "release/approved_draft_validation"

REPORT_JSON = OUT_DIR / "APPROVED_DRAFT_STATIC_VALIDATION_V12_10_36.json"
REPORT_MD = OUT_DIR / "APPROVED_DRAFT_STATIC_VALIDATION_V12_10_36.md"
FORBIDDEN = ROOT / "alembic/versions/0018_APPROVED_MODEL_MIGRATION_DRAFT_V12_10_35.py"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"Missing required file: {path}")
    return json.loads(path.read_text())


def extract_create_tables(text: str) -> List[str]:
    return re.findall(r'op\.create_table\(\s*["\']([^"\']+)["\']', text)


def extract_drop_tables(text: str) -> List[str]:
    return re.findall(r'op\.drop_table\(\s*["\']([^"\']+)["\']', text)


def validate() -> Dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if not DRAFT.exists():
        raise SystemExit(f"Missing draft: {DRAFT}")

    manifest = load_json(MANIFEST)
    approved = manifest.get("approved_tables", [])
    text = DRAFT.read_text()

    create_tables = extract_create_tables(text)
    drop_tables = extract_drop_tables(text)
    todo_count = text.count("TODO")

    approved_set = set(approved)
    create_set = set(create_tables)
    drop_set = set(drop_tables)

    errors = []
    warnings = []

    if FORBIDDEN.exists():
        errors.append(f"forbidden alembic/versions copy exists: {FORBIDDEN}")

    missing_from_upgrade = sorted(approved_set - create_set)
    extra_in_upgrade = sorted(create_set - approved_set)

    if missing_from_upgrade:
        errors.append("approved tables missing from upgrade: " + ", ".join(missing_from_upgrade))

    if extra_in_upgrade:
        errors.append("unapproved tables in upgrade: " + ", ".join(extra_in_upgrade))

    duplicate_creates = sorted({t for t in create_tables if create_tables.count(t) > 1})
    duplicate_drops = sorted({t for t in drop_tables if drop_tables.count(t) > 1})

    if duplicate_creates:
        errors.append("duplicate create_table entries: " + ", ".join(duplicate_creates))

    if duplicate_drops:
        errors.append("duplicate drop_table entries: " + ", ".join(duplicate_drops))

    if create_set != drop_set:
        errors.append("upgrade/downgrade table sets differ")

    expected_downgrade = list(reversed(create_tables))
    if drop_tables != expected_downgrade:
        errors.append("downgrade order is not exact reverse of upgrade order")

    if todo_count == 0:
        warnings.append("no TODO markers found; expected review TODOs in draft")

    promotion_status = "GO" if not errors else "NO-GO"

    report = {
        "version": VERSION,
        "generated_at": now(),
        "promotion_status": promotion_status,
        "schema_mutation": "none",
        "migration_created": False,
        "alembic_versions_mutated": False,
        "alembic_upgrade_run": False,
        "draft": str(DRAFT),
        "manifest": str(MANIFEST),
        "approved_table_count": len(approved),
        "create_table_count": len(create_tables),
        "drop_table_count": len(drop_tables),
        "todo_count": todo_count,
        "approved_tables": approved,
        "create_tables": create_tables,
        "drop_tables": drop_tables,
        "expected_downgrade_order": expected_downgrade,
        "errors": errors,
        "warnings": warnings,
    }

    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True))
    write_md(report)
    return report


def write_md(report: Dict[str, Any]) -> None:
    lines = [
        "# v12.10.36 Approved Draft Static Validation",
        "",
        f"- **promotion_status**: `{report['promotion_status']}`",
        "- **schema_mutation**: `none`",
        "- **migration_created**: `False`",
        "- **alembic_versions_mutated**: `False`",
        "- **alembic_upgrade_run**: `False`",
        f"- **approved_table_count**: `{report['approved_table_count']}`",
        f"- **create_table_count**: `{report['create_table_count']}`",
        f"- **drop_table_count**: `{report['drop_table_count']}`",
        f"- **todo_count**: `{report['todo_count']}`",
        "",
        "## Errors",
        "",
    ]

    if report["errors"]:
        for e in report["errors"]:
            lines.append(f"- {e}")
    else:
        lines.append("- none")

    lines.extend(["", "## Warnings", ""])

    if report["warnings"]:
        for w in report["warnings"]:
            lines.append(f"- {w}")
    else:
        lines.append("- none")

    lines.extend(["", "## Approved / upgrade / downgrade order", ""])

    for i, table in enumerate(report["approved_tables"], 1):
        lines.append(f"{i}. `{table}`")

    REPORT_MD.write_text("\n".join(lines))


def main() -> int:
    report = validate()
    print(json.dumps({
        "version": VERSION,
        "promotion_status": report["promotion_status"],
        "approved_table_count": report["approved_table_count"],
        "create_table_count": report["create_table_count"],
        "drop_table_count": report["drop_table_count"],
        "todo_count": report["todo_count"],
        "error_count": len(report["errors"]),
        "warning_count": len(report["warnings"]),
        "schema_mutation": "none",
        "migration_created": False,
        "alembic_versions_mutated": False,
        "alembic_upgrade_run": False,
        "report_json": str(REPORT_JSON),
        "report_md": str(REPORT_MD),
    }, indent=2, sort_keys=True))
    return 0 if report["promotion_status"] == "GO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
