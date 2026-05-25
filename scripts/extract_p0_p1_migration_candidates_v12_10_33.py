#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path.cwd()
VERSION = "12.10.33"

INPUT_JSON = ROOT / "release/model_migration_reconciliation/MODEL_MIGRATION_RECONCILIATION_V12_10_32.json"
OUT_DIR = ROOT / "release/p0_p1_migration_review"

OUT_JSON = OUT_DIR / "P0_P1_MIGRATION_CANDIDATES_V12_10_33.json"
OUT_CSV = OUT_DIR / "P0_P1_MIGRATION_CANDIDATES_V12_10_33.csv"
OUT_MD = OUT_DIR / "P0_P1_MIGRATION_WORKSHEET_V12_10_33.md"
OUT_DRAFT = OUT_DIR / "NON_EXECUTABLE_ALEMBIC_DRAFT_V12_10_33.py"
OUT_REVIEW = OUT_DIR / "PASS_REVIEW_CLASSIFICATION_V12_10_33.md"


def read(path: Path) -> str:
    try:
        return path.read_text(errors="replace")
    except Exception:
        return ""


def load_input() -> Dict[str, Any]:
    if not INPUT_JSON.exists():
        raise SystemExit(f"Missing input JSON: {INPUT_JSON}. Run make report121032 first.")
    return json.loads(INPUT_JSON.read_text())


def source_window(file_path: str, line_no: int, radius: int = 45) -> Dict[str, Any]:
    p = ROOT / file_path
    lines = read(p).splitlines()
    if not lines:
        return {"file": file_path, "start": 0, "end": 0, "text": ""}

    start = max(1, line_no - radius)
    end = min(len(lines), line_no + radius)
    text = "\n".join(f"{i:04d}: {lines[i-1]}" for i in range(start, end + 1))

    return {"file": file_path, "start": start, "end": end, "text": text}


def extract_model_block(file_path: str, table: str, line_no: int) -> Dict[str, Any]:
    p = ROOT / file_path
    lines = read(p).splitlines()

    if not lines:
        return {"kind": "missing", "name": None, "text": "", "columns": []}

    idx = max(0, min(len(lines) - 1, line_no - 1))

    class_start = None
    class_name = None
    for i in range(idx, max(-1, idx - 180), -1):
        m = re.match(r"^class\s+([A-Za-z_][A-Za-z0-9_]*)\(", lines[i])
        if m:
            class_start = i
            class_name = m.group(1)
            break

    table_start = None
    for i in range(idx, max(-1, idx - 120), -1):
        if re.search(r"\bTable\(\s*['\"]" + re.escape(table) + r"['\"]", lines[i]):
            table_start = i
            break

    if table_start is not None and (class_start is None or table_start >= class_start):
        end = min(len(lines) - 1, table_start + 160)
        block = "\n".join(lines[table_start:end + 1])
        return {
            "kind": "Table()",
            "name": table,
            "start_line": table_start + 1,
            "end_line": end + 1,
            "text": "\n".join(f"{n:04d}: {line}" for n, line in enumerate(lines[table_start:end + 1], table_start + 1)),
            "columns": column_hints(block),
        }

    if class_start is not None:
        end = min(len(lines) - 1, class_start + 160)
        block_lines = []
        for j in range(class_start, end + 1):
            if j > class_start and lines[j].startswith("class "):
                break
            block_lines.append(lines[j])

        block = "\n".join(block_lines)
        return {
            "kind": "class",
            "name": class_name,
            "start_line": class_start + 1,
            "end_line": class_start + len(block_lines),
            "text": "\n".join(f"{n:04d}: {line}" for n, line in enumerate(block_lines, class_start + 1)),
            "columns": column_hints(block),
        }

    win = source_window(file_path, line_no)
    return {
        "kind": "context",
        "name": None,
        "start_line": win["start"],
        "end_line": win["end"],
        "text": win["text"],
        "columns": column_hints(win["text"]),
    }


def column_hints(text: str) -> List[Dict[str, str]]:
    cols: List[Dict[str, str]] = []

    for m in re.finditer(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?:db\.)?Column\((.*?)\)", text, re.M | re.S):
        name = m.group(1)
        expr = re.sub(r"\s+", " ", m.group(2).strip())[:400]
        cols.append({"name": name, "source": "assignment", "expression": expr, "todo": classify_expr(expr)})

    for m in re.finditer(r"(?:sa\.)?Column\(\s*['\"]([^'\"]+)['\"]\s*,\s*(.*?)\)", text, re.M | re.S):
        name = m.group(1)
        expr = re.sub(r"\s+", " ", m.group(2).strip())[:400]
        if not any(c["name"] == name for c in cols):
            cols.append({"name": name, "source": "Column()", "expression": expr, "todo": classify_expr(expr)})

    return cols[:80]


def classify_expr(expr: str) -> str:
    low = expr.lower()
    if "primary_key=true" in low:
        return "confirm primary key"
    if "foreignkey" in low:
        return "confirm FK target and migration order"
    if "unique=true" in low or "index=true" in low:
        return "confirm index/unique constraint"
    if "json" in low:
        return "confirm JSON/JSONB"
    if "datetime" in low:
        return "confirm timezone/default"
    return "confirm type/nullability/default"


def classify_candidate(record: Dict[str, Any], blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
    blockers = []
    warnings = []

    if record.get("priority_bucket") not in {"P0", "P1"}:
        blockers.append("not P0/P1")

    if record.get("status") != "active_candidate":
        blockers.append(f"status is {record.get('status')}, not active_candidate")

    if record.get("indirect_coverage_hints"):
        warnings.append("possible indirect/rename coverage exists")

    if not any(b.get("columns") for b in blocks):
        blockers.append("no SQLAlchemy column hints extracted")

    if blockers:
        result = "REVIEW"
    elif warnings:
        result = "PASS_WITH_REVIEW_NOTES"
    else:
        result = "PASS"

    return {"classification": result, "blockers": blockers, "warnings": warnings}


def build_payload() -> Dict[str, Any]:
    data = load_input()
    records = [
        r for r in data.get("missing_records", [])
        if r.get("priority_bucket") in {"P0", "P1"}
    ]

    output = []
    for r in records:
        extracted = []
        blocks = []

        for src in r.get("sources", []):
            file_path = src["file"]
            line_no = int(src.get("line") or 1)
            block = extract_model_block(file_path, r["table"], line_no)
            blocks.append(block)
            extracted.append({
                "source": src,
                "block": block,
                "context": source_window(file_path, line_no),
            })

        review = classify_candidate(r, blocks)

        output.append({
            "table": r["table"],
            "domain": r.get("domain"),
            "priority_bucket": r.get("priority_bucket"),
            "priority_score": r.get("priority_score"),
            "status": r.get("status"),
            "migration_action": r.get("migration_action"),
            "priority_reasons": r.get("priority_reasons", []),
            "indirect_coverage_hints": r.get("indirect_coverage_hints", []),
            "sources": r.get("sources", []),
            "reference_count": r.get("reference_count"),
            "reference_files": r.get("reference_files", []),
            "extracted": extracted,
            "review": review,
        })

    summary = {
        "version": VERSION,
        "input": str(INPUT_JSON),
        "candidate_count": len(output),
        "p0_count": sum(1 for r in output if r["priority_bucket"] == "P0"),
        "p1_count": sum(1 for r in output if r["priority_bucket"] == "P1"),
        "pass_count": sum(1 for r in output if r["review"]["classification"] == "PASS"),
        "pass_with_review_notes_count": sum(1 for r in output if r["review"]["classification"] == "PASS_WITH_REVIEW_NOTES"),
        "review_count": sum(1 for r in output if r["review"]["classification"] == "REVIEW"),
        "schema_mutation": "none",
        "migration_created": False,
        "alembic_versions_mutated": False,
    }

    return {"summary": summary, "records": output}


def write_outputs(payload: Dict[str, Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    OUT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True))

    with OUT_CSV.open("w", newline="") as f:
        fields = [
            "classification", "priority_bucket", "priority_score", "table",
            "domain", "status", "migration_action", "column_count",
            "blockers", "warnings", "sources"
        ]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()

        for r in payload["records"]:
            col_count = sum(len(e["block"].get("columns", [])) for e in r["extracted"])
            writer.writerow({
                "classification": r["review"]["classification"],
                "priority_bucket": r["priority_bucket"],
                "priority_score": r["priority_score"],
                "table": r["table"],
                "domain": r["domain"],
                "status": r["status"],
                "migration_action": r["migration_action"],
                "column_count": col_count,
                "blockers": "; ".join(r["review"]["blockers"]),
                "warnings": "; ".join(r["review"]["warnings"]),
                "sources": "; ".join(sorted({s["file"] for s in r["sources"]})),
            })

    write_md(payload)
    write_draft(payload)
    write_review(payload)


def write_md(payload: Dict[str, Any]) -> None:
    s = payload["summary"]
    lines = [
        "# v12.10.33 P0/P1 Migration Candidate Worksheet",
        "",
        "- **schema_mutation**: `none`",
        "- **migration_created**: `False`",
        "- **alembic_versions_mutated**: `False`",
        f"- **candidate_count**: `{s['candidate_count']}`",
        f"- **P0**: `{s['p0_count']}`",
        f"- **P1**: `{s['p1_count']}`",
        f"- **PASS**: `{s['pass_count']}`",
        f"- **PASS_WITH_REVIEW_NOTES**: `{s['pass_with_review_notes_count']}`",
        f"- **REVIEW**: `{s['review_count']}`",
        "",
        "## Summary table",
        "",
        "| Class | Priority | Score | Table | Domain | Status | Columns | Notes |",
        "|---|---|---:|---|---|---|---:|---|",
    ]

    for r in payload["records"]:
        col_count = sum(len(e["block"].get("columns", [])) for e in r["extracted"])
        notes = []
        if r["review"]["blockers"]:
            notes.append("BLOCKERS: " + "; ".join(r["review"]["blockers"]))
        if r["review"]["warnings"]:
            notes.append("WARNINGS: " + "; ".join(r["review"]["warnings"]))
        if not notes:
            notes.append("ready for human column review")

        lines.append(
            f"| {r['review']['classification']} | {r['priority_bucket']} | {r['priority_score']} | `{r['table']}` | {r['domain']} | {r['status']} | {col_count} | {'<br>'.join(notes)} |"
        )

    lines.append("")
    lines.append("## Candidate details")
    lines.append("")

    for r in payload["records"]:
        lines.extend([
            f"### `{r['table']}`",
            "",
            f"- classification: `{r['review']['classification']}`",
            f"- priority: `{r['priority_bucket']}` / `{r['priority_score']}`",
            f"- domain: `{r['domain']}`",
            f"- status: `{r['status']}`",
            f"- migration_action: `{r['migration_action']}`",
            "",
            "Sources:",
        ])

        for src in r["sources"]:
            lines.append(f"- `{src['file']}:{src['line']}` ({src.get('kind')})")

        if r["indirect_coverage_hints"]:
            lines.append("")
            lines.append("Possible indirect/rename coverage:")
            for hint in r["indirect_coverage_hints"]:
                lines.append(f"- `{hint['migration_table']}` — {hint['reason']} ({hint['strength']})")

        for idx, e in enumerate(r["extracted"], 1):
            b = e["block"]
            lines.extend([
                "",
                f"#### Extracted block {idx}: {b['kind']} `{b.get('name')}` lines {b.get('start_line')}-{b.get('end_line')}",
                "",
                "```python",
                b.get("text", "")[:10000],
                "```",
                "",
                "Column hints:",
            ])

            if not b.get("columns"):
                lines.append("- none detected")
            else:
                for col in b["columns"]:
                    lines.append(f"- `{col['name']}` — `{col['expression']}` — TODO: {col['todo']}")

            lines.append("")

    OUT_MD.write_text("\n".join(lines))


def draft_type(expr: str) -> str:
    low = expr.lower()
    if "integer" in low:
        return "sa.Integer()"
    if "string" in low:
        return "sa.String(length=TODO)"
    if "text" in low:
        return "sa.Text()"
    if "datetime" in low:
        return "sa.DateTime(timezone=True)"
    if "boolean" in low:
        return "sa.Boolean()"
    if "float" in low:
        return "sa.Float()"
    if "json" in low:
        return "sa.JSON()  # TODO confirm JSON/JSONB"
    return "sa.String()  # TODO confirm type"


def write_draft(payload: Dict[str, Any]) -> None:
    lines = [
        '"""NON-EXECUTABLE REVIEW DRAFT — v12.10.33',
        "",
        "This file is intentionally generated outside alembic/versions.",
        "Do not copy into alembic/versions until each table/column is reviewed.",
        "",
        "Revision ID: 0018_REVIEW_ONLY_p0_p1_candidate_tables",
        "Revises: 0017_v12_10_schema_reconciliation",
        '"""',
        "",
        "# REVIEW ONLY — NOT A REAL MIGRATION",
        "# Schema mutation: none",
        "",
        "from alembic import op",
        "import sqlalchemy as sa",
        "",
        'revision = "0018_REVIEW_ONLY_p0_p1_candidate_tables"',
        'down_revision = "0017_v12_10_schema_reconciliation"',
        "branch_labels = None",
        "depends_on = None",
        "",
        "def upgrade():",
        '    raise RuntimeError("NON-EXECUTABLE REVIEW DRAFT: do not run")',
        "",
    ]

    for r in payload["records"]:
        lines.append(f"    # Candidate: {r['table']} ({r['priority_bucket']} / {r['review']['classification']})")
        lines.append(f"    # domain: {r['domain']}")
        lines.append(f"    # status: {r['status']}")

        cols = []
        for e in r["extracted"]:
            for col in e["block"].get("columns", []):
                if col["name"] not in [c["name"] for c in cols]:
                    cols.append(col)

        lines.append(f"    # op.create_table(")
        lines.append(f'    #     "{r["table"]}",')
        if not cols:
            lines.append("    #     # TODO: no columns extracted; review source manually")
        else:
            for col in cols:
                lines.append(f'    #     sa.Column("{col["name"]}", {draft_type(col["expression"]) }),  # TODO: {col["todo"]}')
        lines.append("    # )")
        lines.append("")

    lines.extend([
        "",
        "def downgrade():",
        '    raise RuntimeError("NON-EXECUTABLE REVIEW DRAFT: do not run")',
    ])

    OUT_DRAFT.write_text("\n".join(lines))


def write_review(payload: Dict[str, Any]) -> None:
    lines = [
        "# v12.10.33 PASS/REVIEW Classification",
        "",
        "| Classification | Table | Priority | Domain | Blockers | Warnings |",
        "|---|---|---|---|---|---|",
    ]

    for r in payload["records"]:
        lines.append(
            f"| {r['review']['classification']} | `{r['table']}` | {r['priority_bucket']} | {r['domain']} | {'; '.join(r['review']['blockers']) or '-'} | {'; '.join(r['review']['warnings']) or '-'} |"
        )

    OUT_REVIEW.write_text("\n".join(lines))


def main() -> int:
    payload = build_payload()
    write_outputs(payload)

    print(json.dumps({
        **payload["summary"],
        "report_json": str(OUT_JSON),
        "report_csv": str(OUT_CSV),
        "worksheet": str(OUT_MD),
        "non_executable_draft": str(OUT_DRAFT),
        "classification": str(OUT_REVIEW),
    }, indent=2, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
