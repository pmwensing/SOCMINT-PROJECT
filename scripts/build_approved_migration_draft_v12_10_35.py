#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path.cwd()
VERSION = "12.10.35"

APPROVED_SET = ROOT / "release/human_review_gate/approved_migration_set.json"
CANDIDATES_JSON = ROOT / "release/p0_p1_migration_review/P0_P1_MIGRATION_CANDIDATES_V12_10_33.json"

OUT_DIR = ROOT / "release/approved_migration_draft"
DRAFT = OUT_DIR / "0018_APPROVED_MODEL_MIGRATION_DRAFT_V12_10_35.py"
MANIFEST = OUT_DIR / "APPROVED_MIGRATION_DRAFT_MANIFEST_V12_10_35.json"
REPORT_MD = OUT_DIR / "APPROVED_MIGRATION_DRAFT_REPORT_V12_10_35.md"
REFUSAL_MD = OUT_DIR / "APPROVED_MIGRATION_DRAFT_REFUSAL_V12_10_35.md"

FORBIDDEN_ALEMBIC_PATH = ROOT / "alembic/versions/0018_APPROVED_MODEL_MIGRATION_DRAFT_V12_10_35.py"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"Missing required JSON file: {path}")
    return json.loads(path.read_text())


def ensure_no_schema_mutation() -> None:
    if FORBIDDEN_ALEMBIC_PATH.exists():
        raise SystemExit(f"Forbidden Alembic versions mutation detected: {FORBIDDEN_ALEMBIC_PATH}")


def compact(expr: str) -> str:
    return re.sub(r"\s+", " ", expr.strip())


def sa_type_from_expr(expr: str) -> str:
    low = expr.lower()

    if "uuid" in low:
        return "sa.String(36)  # TODO: confirm UUID dialect"
    if "integer" in low or "bigint" in low:
        return "sa.Integer()"
    if "string" in low:
        m = re.search(r"string\((\d+)\)", low)
        if m:
            return f"sa.String({m.group(1)})"
        return "sa.String(length=TODO)"
    if "text" in low:
        return "sa.Text()"
    if "datetime" in low or "timestamp" in low:
        return "sa.DateTime(timezone=True)  # TODO: confirm timezone/default"
    if "date" in low:
        return "sa.Date()"
    if "boolean" in low:
        return "sa.Boolean()"
    if "float" in low:
        return "sa.Float()"
    if "numeric" in low or "decimal" in low:
        return "sa.Numeric()  # TODO: confirm precision/scale"
    if "jsonb" in low:
        return "sa.JSON()  # TODO: confirm JSONB dialect"
    if "json" in low:
        return "sa.JSON()"

    return "sa.String()  # TODO: confirm type"


def column_flags(expr: str) -> List[str]:
    low = compact(expr).lower()
    flags = []

    if "primary_key=true" in low:
        flags.append("primary_key=True")
    if "nullable=false" in low:
        flags.append("nullable=False")
    if "unique=true" in low:
        flags.append("unique=True")
    if "index=true" in low:
        flags.append("index=True")

    # Do not auto-copy defaults blindly. Keep TODO comments instead.
    return flags


def collect_columns(candidate: Dict[str, Any]) -> List[Dict[str, Any]]:
    columns: List[Dict[str, Any]] = []
    seen = set()

    for extracted in candidate.get("extracted", []):
        block = extracted.get("block", {})
        for col in block.get("columns", []):
            name = col.get("name")
            if not name or name in seen:
                continue
            seen.add(name)

            expr = col.get("expression", "")
            columns.append({
                "name": name,
                "expression": expr,
                "sa_type": sa_type_from_expr(expr),
                "flags": column_flags(expr),
                "todo": col.get("todo", "confirm type/nullability/default"),
            })

    return columns


def load_candidate_map() -> Dict[str, Any]:
    data = read_json(CANDIDATES_JSON)
    return {r["table"]: r for r in data.get("records", [])}


def load_and_validate() -> Dict[str, Any]:
    ensure_no_schema_mutation()

    approved = read_json(APPROVED_SET)
    candidates = load_candidate_map()

    validation = approved.get("validation", {})
    errors = []

    if not validation.get("valid"):
        errors.append("approved_migration_set validation.valid is false")

    approved_tables = approved.get("approved_tables", [])
    if not approved_tables:
        errors.append("approved_migration_set approved_tables is empty")

    table_names = [t.get("table") for t in approved_tables if isinstance(t, dict)]
    if not table_names:
        errors.append("approved_migration_set has no selected table names")

    unknown = sorted(set(table_names) - set(candidates))
    if unknown:
        errors.append("approved_migration_set references unknown candidate tables: " + ", ".join(unknown))

    records = []
    for table in table_names:
        if table not in candidates:
            continue

        cand = candidates[table]
        classification = cand.get("review", {}).get("classification")

        # Only allow REVIEW/PASS_WITH_REVIEW_NOTES if they were explicitly selected.
        # This is a draft, but still preserve warning metadata.
        approved_entry = next((x for x in approved_tables if x.get("table") == table), {})
        records.append({
            "table": table,
            "candidate": cand,
            "approved_entry": approved_entry,
            "classification": classification,
            "columns": collect_columns(cand),
        })

    if not records:
        errors.append("no valid approved candidate records could be loaded")

    for r in records:
        if not r["columns"]:
            errors.append(f"{r['table']}: no columns extracted; cannot draft table safely")

    if errors:
        write_refusal(errors, approved)
        raise SystemExit("v12.10.35 refused to build draft:\n- " + "\n- ".join(errors))

    return {
        "approved": approved,
        "records": records,
    }


def write_refusal(errors: List[str], approved: Dict[str, Any] | None = None) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    lines = [
        "# v12.10.35 Approved Migration Draft Refusal",
        "",
        "The approved migration draft was refused.",
        "",
        "## Errors",
        "",
    ]

    for err in errors:
        lines.append(f"- {err}")

    lines.extend([
        "",
        "## Safety status",
        "",
        "- schema_mutation: `none`",
        "- migration_created: `false`",
        "- alembic_versions_mutated: `false`",
        "- alembic_upgrade_run: `false`",
        "",
    ])

    if approved is not None:
        lines.extend([
            "## Approval metadata observed",
            "",
            "```json",
            json.dumps({
                "approved_by": approved.get("approved_by"),
                "approval_date": approved.get("approval_date"),
                "validation": approved.get("validation"),
            }, indent=2, sort_keys=True),
            "```",
        ])

    REFUSAL_MD.write_text("\n".join(lines))


def build_draft(context: Dict[str, Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    records = context["records"]

    lines = [
        '"""v12.10.35 APPROVED MIGRATION DRAFT — REVIEW BEFORE PROMOTION',
        "",
        "This file is generated outside alembic/versions.",
        "It is not applied automatically.",
        "Promote only after human review of every TODO.",
        "",
        "Revision ID: 0018_approved_model_migration",
        "Revises: 0017_v12_10_schema_reconciliation",
        '"""',
        "",
        "# REVIEW DRAFT ONLY.",
        "# Do not run until promoted in a later build.",
        "",
        "from alembic import op",
        "import sqlalchemy as sa",
        "",
        'revision = "0018_approved_model_migration"',
        'down_revision = "0017_v12_10_schema_reconciliation"',
        "branch_labels = None",
        "depends_on = None",
        "",
        "",
        "def upgrade():",
    ]

    for rec in records:
        table = rec["table"]
        cand = rec["candidate"]
        classification = rec["classification"]
        domain = cand.get("domain")
        priority = cand.get("priority_bucket")

        lines.extend([
            f"    # --- approved table: {table} ---",
            f"    # classification: {classification}",
            f"    # priority: {priority}",
            f"    # domain: {domain}",
            "    op.create_table(",
            f'        "{table}",',
        ])

        for col in rec["columns"]:
            args = [f'"{col["name"]}"', col["sa_type"]]
            args.extend(col["flags"])
            arg_str = ", ".join(args)
            lines.append(f"        sa.Column({arg_str}),  # TODO: {col['todo']}")

        lines.append("    )")
        lines.append("")

    lines.extend([
        "",
        "def downgrade():",
        "    # Reverse dependency order.",
    ])

    for rec in reversed(records):
        lines.append(f'    op.drop_table("{rec["table"]}")')

    DRAFT.write_text("\n".join(lines))


def build_manifest(context: Dict[str, Any]) -> Dict[str, Any]:
    approved = context["approved"]
    records = context["records"]

    classifications = {}
    for rec in records:
        classifications.setdefault(rec["classification"], 0)
        classifications[rec["classification"]] += 1

    manifest = {
        "version": VERSION,
        "generated_at": utc_now(),
        "schema_mutation": "none",
        "migration_created": False,
        "alembic_versions_mutated": False,
        "alembic_upgrade_run": False,
        "draft_created": True,
        "draft_path": str(DRAFT),
        "approved_source": str(APPROVED_SET),
        "approved_by": approved.get("approved_by"),
        "approval_date": approved.get("approval_date"),
        "approved_table_count": len(records),
        "approved_tables": [r["table"] for r in records],
        "classification_counts": classifications,
        "downgrade_order": [r["table"] for r in reversed(records)],
        "safety_checks": {
            "approval_valid": approved.get("validation", {}).get("valid"),
            "no_alembic_versions_write": not FORBIDDEN_ALEMBIC_PATH.exists(),
            "no_schema_mutation": True,
            "no_alembic_upgrade": True,
        },
    }

    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True))
    return manifest


def write_report(context: Dict[str, Any], manifest: Dict[str, Any]) -> None:
    records = context["records"]

    lines = [
        "# v12.10.35 Approved Migration Draft Report",
        "",
        "- **schema_mutation**: `none`",
        "- **migration_created**: `False`",
        "- **alembic_versions_mutated**: `False`",
        "- **alembic_upgrade_run**: `False`",
        f"- **draft_created**: `{manifest['draft_created']}`",
        f"- **approved_table_count**: `{manifest['approved_table_count']}`",
        f"- **draft_path**: `{manifest['draft_path']}`",
        "",
        "## Approved tables",
        "",
        "| Table | Classification | Domain | Priority | Columns |",
        "|---|---|---|---|---:|",
    ]

    for rec in records:
        cand = rec["candidate"]
        lines.append(
            f"| `{rec['table']}` | {rec['classification']} | {cand.get('domain')} | {cand.get('priority_bucket')} | {len(rec['columns'])} |"
        )

    lines.extend([
        "",
        "## Downgrade order",
        "",
    ])

    for table in manifest["downgrade_order"]:
        lines.append(f"- `{table}`")

    lines.extend([
        "",
        "## Next required step",
        "",
        "Review `0018_APPROVED_MODEL_MIGRATION_DRAFT_V12_10_35.py` manually.",
        "Do not copy it into `alembic/versions` until a future promotion build explicitly approves it.",
    ])

    REPORT_MD.write_text("\n".join(lines))


def main() -> int:
    ensure_no_schema_mutation()
    context = load_and_validate()
    build_draft(context)
    manifest = build_manifest(context)
    write_report(context, manifest)
    ensure_no_schema_mutation()

    print(json.dumps({
        "version": VERSION,
        "draft_created": True,
        "approved_table_count": manifest["approved_table_count"],
        "schema_mutation": "none",
        "migration_created": False,
        "alembic_versions_mutated": False,
        "alembic_upgrade_run": False,
        "draft_path": str(DRAFT),
        "manifest": str(MANIFEST),
        "report": str(REPORT_MD),
    }, indent=2, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
