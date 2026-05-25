#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set


ROOT = Path.cwd()
VERSION = "12.10.34"

INPUT_JSON = ROOT / "release/p0_p1_migration_review/P0_P1_MIGRATION_CANDIDATES_V12_10_33.json"

OUT_DIR = ROOT / "release/human_review_gate"
CHECKLIST_MD = OUT_DIR / "HUMAN_REVIEW_CHECKLIST_V12_10_34.md"
CHECKLIST_CSV = OUT_DIR / "HUMAN_REVIEW_CHECKLIST_V12_10_34.csv"
QUEUES_JSON = OUT_DIR / "REVIEW_QUEUES_V12_10_34.json"
APPROVAL_TEMPLATE = OUT_DIR / "APPROVAL_LIST_TEMPLATE_V12_10_34.json"
APPROVED_SET = OUT_DIR / "approved_migration_set.json"
REFUSAL_MD = OUT_DIR / "MIGRATION_CREATION_REFUSAL_V12_10_34.md"
SUMMARY_JSON = OUT_DIR / "HUMAN_REVIEW_GATE_SUMMARY_V12_10_34.json"
SUMMARY_MD = OUT_DIR / "HUMAN_REVIEW_GATE_SUMMARY_V12_10_34.md"

# Optional user-created file. This must be edited manually by the operator.
APPROVAL_INPUT = OUT_DIR / "approval_list.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_candidates() -> Dict[str, Any]:
    if not INPUT_JSON.exists():
        raise SystemExit(f"Missing v12.10.33 input: {INPUT_JSON}. Run make report121033 first.")
    return json.loads(INPUT_JSON.read_text())


def classify_queues(records: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    queues = {
        "PASS": [],
        "PASS_WITH_REVIEW_NOTES": [],
        "REVIEW": [],
    }

    for record in records:
        cls = record.get("review", {}).get("classification", "REVIEW")
        queues.setdefault(cls, []).append(record)

    return queues


def record_brief(record: Dict[str, Any]) -> Dict[str, Any]:
    extracted = record.get("extracted", [])
    column_count = 0
    source_files = set()

    for item in extracted:
        block = item.get("block", {})
        column_count += len(block.get("columns", []))

    for src in record.get("sources", []):
        source_files.add(src.get("file", ""))

    return {
        "table": record.get("table"),
        "domain": record.get("domain"),
        "priority_bucket": record.get("priority_bucket"),
        "priority_score": record.get("priority_score"),
        "status": record.get("status"),
        "classification": record.get("review", {}).get("classification"),
        "blockers": record.get("review", {}).get("blockers", []),
        "warnings": record.get("review", {}).get("warnings", []),
        "migration_action": record.get("migration_action"),
        "column_count": column_count,
        "source_files": sorted(x for x in source_files if x),
        "indirect_coverage_hints": record.get("indirect_coverage_hints", []),
    }


def write_checklist(payload: Dict[str, Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    records = payload["records"]
    queues = classify_queues(records)

    lines = [
        "# v12.10.34 Human Review Checklist",
        "",
        "- **schema_mutation**: `none`",
        "- **migration_created**: `False`",
        "- **alembic_versions_mutated**: `False`",
        f"- **candidate_count**: `{len(records)}`",
        f"- **PASS queue**: `{len(queues.get('PASS', []))}`",
        f"- **PASS_WITH_REVIEW_NOTES queue**: `{len(queues.get('PASS_WITH_REVIEW_NOTES', []))}`",
        f"- **REVIEW queue**: `{len(queues.get('REVIEW', []))}`",
        "",
        "## Instructions",
        "",
        "1. Review every table below.",
        "2. Do not approve any table with unresolved blockers.",
        "3. For PASS_WITH_REVIEW_NOTES, confirm warning notes manually.",
        "4. For REVIEW, resolve blockers before approval.",
        "5. Create/edit `release/human_review_gate/approval_list.json` manually.",
        "6. Run `make approve121034` to build `approved_migration_set.json`.",
        "",
        "## Required approval file format",
        "",
        "```json",
        json.dumps({
            "approved_by": "human-name-or-initials",
            "approval_date": "YYYY-MM-DD",
            "approved_tables": ["table_name_here"],
            "notes": "manual review notes"
        }, indent=2),
        "```",
        "",
        "## Checklist",
        "",
        "| Approve? | Classification | Priority | Table | Domain | Columns | Blockers | Warnings | Sources |",
        "|---|---|---|---|---|---:|---|---|---|",
    ]

    for record in records:
        brief = record_brief(record)
        blockers = "; ".join(brief["blockers"]) if brief["blockers"] else "-"
        warnings = "; ".join(brief["warnings"]) if brief["warnings"] else "-"
        sources = "<br>".join(brief["source_files"][:5]) if brief["source_files"] else "-"
        lines.append(
            f"| ☐ | {brief['classification']} | {brief['priority_bucket']} | `{brief['table']}` | {brief['domain']} | {brief['column_count']} | {blockers} | {warnings} | {sources} |"
        )

    for queue_name in ["PASS", "PASS_WITH_REVIEW_NOTES", "REVIEW"]:
        lines.extend(["", f"## Queue: {queue_name}", ""])

        for record in queues.get(queue_name, []):
            brief = record_brief(record)
            lines.extend([
                f"### `{brief['table']}`",
                "",
                f"- classification: `{brief['classification']}`",
                f"- priority: `{brief['priority_bucket']}` / `{brief['priority_score']}`",
                f"- domain: `{brief['domain']}`",
                f"- status: `{brief['status']}`",
                f"- migration_action: `{brief['migration_action']}`",
                f"- column_count: `{brief['column_count']}`",
                "",
            ])

            if brief["blockers"]:
                lines.append("Blockers:")
                for item in brief["blockers"]:
                    lines.append(f"- {item}")
                lines.append("")

            if brief["warnings"]:
                lines.append("Warnings:")
                for item in brief["warnings"]:
                    lines.append(f"- {item}")
                lines.append("")

            if brief["indirect_coverage_hints"]:
                lines.append("Possible indirect/rename coverage:")
                for hint in brief["indirect_coverage_hints"]:
                    lines.append(f"- `{hint.get('migration_table')}` — {hint.get('reason')} ({hint.get('strength')})")
                lines.append("")

            lines.append("Sources:")
            for src in brief["source_files"]:
                lines.append(f"- `{src}`")
            lines.append("")

    CHECKLIST_MD.write_text("\n".join(lines))

    with CHECKLIST_CSV.open("w", newline="") as f:
        fields = [
            "approve",
            "classification",
            "priority_bucket",
            "priority_score",
            "table",
            "domain",
            "status",
            "column_count",
            "blockers",
            "warnings",
            "migration_action",
            "source_files",
        ]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()

        for record in records:
            brief = record_brief(record)
            writer.writerow({
                "approve": "",
                "classification": brief["classification"],
                "priority_bucket": brief["priority_bucket"],
                "priority_score": brief["priority_score"],
                "table": brief["table"],
                "domain": brief["domain"],
                "status": brief["status"],
                "column_count": brief["column_count"],
                "blockers": "; ".join(brief["blockers"]),
                "warnings": "; ".join(brief["warnings"]),
                "migration_action": brief["migration_action"],
                "source_files": "; ".join(brief["source_files"]),
            })


def write_queues(payload: Dict[str, Any]) -> Dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    queues = classify_queues(payload["records"])

    queue_payload = {
        "version": VERSION,
        "generated_at": utc_now(),
        "schema_mutation": "none",
        "migration_created": False,
        "queues": {
            name: [record_brief(r) for r in records]
            for name, records in queues.items()
        },
        "queue_counts": {
            name: len(records)
            for name, records in queues.items()
        },
    }

    QUEUES_JSON.write_text(json.dumps(queue_payload, indent=2, sort_keys=True))
    return queue_payload


def write_approval_template(payload: Dict[str, Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    records = payload["records"]
    pass_tables = [
        r["table"] for r in records
        if r.get("review", {}).get("classification") == "PASS"
    ]

    template = {
        "version": VERSION,
        "approved_by": "",
        "approval_date": "",
        "approved_tables": [],
        "suggested_pass_tables_for_review_only_do_not_auto_approve": pass_tables,
        "notes": "",
        "required_statement": "I manually reviewed the selected tables, source model definitions, blockers, warnings, and column TODOs.",
    }

    APPROVAL_TEMPLATE.write_text(json.dumps(template, indent=2, sort_keys=True))

    if not APPROVAL_INPUT.exists():
        APPROVAL_INPUT.write_text(json.dumps({
            "version": VERSION,
            "approved_by": "",
            "approval_date": "",
            "approved_tables": [],
            "notes": "",
            "required_statement": "I manually reviewed the selected tables, source model definitions, blockers, warnings, and column TODOs."
        }, indent=2, sort_keys=True))


def load_approval_file(path: Path = APPROVAL_INPUT) -> Dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"Approval file missing: {path}")

    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid approval JSON: {exc}") from exc


def validate_approval(payload: Dict[str, Any], approval: Dict[str, Any]) -> Dict[str, Any]:
    records = payload["records"]
    by_table = {r["table"]: r for r in records}
    approved_tables = approval.get("approved_tables", [])

    errors = []
    warnings = []

    if not approval.get("approved_by"):
        errors.append("approved_by is required")

    if not approval.get("approval_date"):
        errors.append("approval_date is required")

    if not isinstance(approved_tables, list):
        errors.append("approved_tables must be a list")
        approved_tables = []

    if not approval.get("required_statement"):
        errors.append("required_statement is required")

    unknown = sorted(set(approved_tables) - set(by_table))
    if unknown:
        errors.append(f"approved_tables contains unknown candidates: {', '.join(unknown)}")

    selected = []
    for table in approved_tables:
        if table not in by_table:
            continue

        record = by_table[table]
        brief = record_brief(record)
        cls = brief["classification"]

        if cls == "REVIEW":
            warnings.append(f"{table}: classification REVIEW; blockers must be documented manually")
        elif cls == "PASS_WITH_REVIEW_NOTES":
            warnings.append(f"{table}: PASS_WITH_REVIEW_NOTES; warnings must be documented manually")

        selected.append({
            **brief,
            "approval_classification_warning": cls in {"REVIEW", "PASS_WITH_REVIEW_NOTES"},
        })

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "selected": selected,
        "approved_table_count": len(selected),
    }


def build_approved_set(payload: Dict[str, Any], approval_path: Path = APPROVAL_INPUT) -> Dict[str, Any]:
    approval = load_approval_file(approval_path)
    validation = validate_approval(payload, approval)

    approved_set = {
        "version": VERSION,
        "generated_at": utc_now(),
        "schema_mutation": "none",
        "migration_created": False,
        "alembic_versions_mutated": False,
        "approval_source": str(approval_path),
        "approved_by": approval.get("approved_by"),
        "approval_date": approval.get("approval_date"),
        "notes": approval.get("notes", ""),
        "validation": validation,
        "approved_tables": validation["selected"],
        "refusal_policy": {
            "create_executable_migration": False,
            "reason": "v12.10.34 is a human review gate only. Executable Alembic migration generation is refused by design.",
        },
    }

    APPROVED_SET.write_text(json.dumps(approved_set, indent=2, sort_keys=True))
    return approved_set


def write_refusal() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    lines = [
        "# v12.10.34 Migration Creation Refusal",
        "",
        "This build refuses to create an executable Alembic migration.",
        "",
        "Reasons:",
        "",
        "1. v12.10.34 is a human review gate only.",
        "2. The P0/P1 candidate list still requires explicit human approval.",
        "3. Column definitions still contain TODO review items.",
        "4. Tables marked REVIEW or PASS_WITH_REVIEW_NOTES require manual sign-off.",
        "5. Schema mutation must not occur until `approved_migration_set.json` is reviewed.",
        "",
        "Allowed outputs:",
        "",
        "- Human review checklist",
        "- Review queues",
        "- Approval template",
        "- `approved_migration_set.json` metadata after approval file is supplied",
        "",
        "Forbidden in this build:",
        "",
        "- Writing to `alembic/versions`",
        "- Running `alembic revision`",
        "- Running `alembic upgrade`",
        "- Creating executable migration files",
        "- Modifying database schema",
        "",
    ]

    REFUSAL_MD.write_text("\n".join(lines))


def write_summary(payload: Dict[str, Any], queue_payload: Dict[str, Any], approved_set: Dict[str, Any] | None) -> Dict[str, Any]:
    summary = {
        "version": VERSION,
        "generated_at": utc_now(),
        "candidate_count": len(payload["records"]),
        "queue_counts": queue_payload["queue_counts"],
        "approval_file_exists": APPROVAL_INPUT.exists(),
        "approved_set_created": approved_set is not None,
        "approved_table_count": approved_set["validation"]["approved_table_count"] if approved_set else 0,
        "approval_valid": approved_set["validation"]["valid"] if approved_set else False,
        "schema_mutation": "none",
        "migration_created": False,
        "alembic_versions_mutated": False,
        "refused_to_create_executable_migration": True,
        "outputs": {
            "checklist_md": str(CHECKLIST_MD),
            "checklist_csv": str(CHECKLIST_CSV),
            "queues_json": str(QUEUES_JSON),
            "approval_template": str(APPROVAL_TEMPLATE),
            "approval_input": str(APPROVAL_INPUT),
            "approved_migration_set": str(APPROVED_SET),
            "refusal_md": str(REFUSAL_MD),
        },
    }

    SUMMARY_JSON.write_text(json.dumps(summary, indent=2, sort_keys=True))

    lines = [
        "# v12.10.34 Human Review Gate Summary",
        "",
        f"- **candidate_count**: `{summary['candidate_count']}`",
        f"- **approval_file_exists**: `{summary['approval_file_exists']}`",
        f"- **approved_set_created**: `{summary['approved_set_created']}`",
        f"- **approved_table_count**: `{summary['approved_table_count']}`",
        f"- **approval_valid**: `{summary['approval_valid']}`",
        "- **schema_mutation**: `none`",
        "- **migration_created**: `False`",
        "- **alembic_versions_mutated**: `False`",
        "- **refused_to_create_executable_migration**: `True`",
        "",
        "## Queue counts",
        "",
    ]

    for name, count in summary["queue_counts"].items():
        lines.append(f"- **{name}**: `{count}`")

    lines.extend([
        "",
        "## Outputs",
        "",
    ])

    for key, value in summary["outputs"].items():
        lines.append(f"- **{key}**: `{value}`")

    SUMMARY_MD.write_text("\n".join(lines))
    return summary


def ensure_no_alembic_mutation() -> None:
    forbidden = ROOT / "alembic" / "versions" / "0018_REVIEW_ONLY_p0_p1_candidate_tables.py"
    if forbidden.exists():
        raise SystemExit(f"Forbidden executable/review migration found in alembic/versions: {forbidden}")


def run_generate() -> Dict[str, Any]:
    ensure_no_alembic_mutation()
    payload = load_candidates()
    write_checklist(payload)
    queue_payload = write_queues(payload)
    write_approval_template(payload)
    write_refusal()
    summary = write_summary(payload, queue_payload, None)
    ensure_no_alembic_mutation()
    return summary


def run_approve() -> Dict[str, Any]:
    ensure_no_alembic_mutation()
    payload = load_candidates()
    write_checklist(payload)
    queue_payload = write_queues(payload)
    write_approval_template(payload)
    write_refusal()

    if not APPROVAL_INPUT.exists():
        raise SystemExit(f"Approval file missing: {APPROVAL_INPUT}")

    approved_set = build_approved_set(payload, APPROVAL_INPUT)
    summary = write_summary(payload, queue_payload, approved_set)
    ensure_no_alembic_mutation()
    return summary


def run_refuse_migration() -> Dict[str, Any]:
    ensure_no_alembic_mutation()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_refusal()

    refusal = {
        "version": VERSION,
        "schema_mutation": "none",
        "migration_created": False,
        "alembic_versions_mutated": False,
        "refused": True,
        "reason": "Executable Alembic migration generation is intentionally refused in v12.10.34.",
        "required_next_step": "Review approval_list.json and use v12.10.35+ for explicitly approved migration drafting.",
        "refusal_md": str(REFUSAL_MD),
    }

    print(json.dumps(refusal, indent=2, sort_keys=True))
    return refusal


def main() -> int:
    parser = argparse.ArgumentParser(description="v12.10.34 Human Review Gate")
    parser.add_argument(
        "mode",
        nargs="?",
        default="generate",
        choices=["generate", "approve", "refuse-migration"],
        help="generate review gate outputs, approve using approval_list.json, or refuse migration creation",
    )

    args = parser.parse_args()

    if args.mode == "generate":
        summary = run_generate()
    elif args.mode == "approve":
        summary = run_approve()
    else:
        summary = run_refuse_migration()

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
