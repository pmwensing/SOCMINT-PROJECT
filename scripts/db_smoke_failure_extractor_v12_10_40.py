#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path.cwd()
VERSION = "12.10.40"

SMOKE_JSON = ROOT / "release/db_migration_smoke/DB_MIGRATION_SMOKE_V12_10_38.json"
GATE_JSON = ROOT / "release/db_smoke_gate/DB_SMOKE_RESULT_GATE_V12_10_39.json"
PROMOTED = ROOT / "migrations/versions/0018_approved_model_migration.py"

OUT_DIR = ROOT / "release/db_smoke_failure"
REPORT_JSON = OUT_DIR / "DB_SMOKE_FAILURE_EXTRACTOR_V12_10_40.json"
REPORT_MD = OUT_DIR / "DB_SMOKE_FAILURE_EXTRACTOR_V12_10_40.md"
PATCH_PLAN = OUT_DIR / "DB_SMOKE_REPAIR_TARGETS_V12_10_40.md"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"Missing required file: {path}")
    return json.loads(path.read_text())


def read(path: Path) -> str:
    try:
        return path.read_text(errors="replace")
    except Exception:
        return ""


def extract_error_lines(text: str) -> List[str]:
    lines = []
    for line in text.splitlines():
        low = line.lower()
        if any(k in low for k in [
            "traceback",
            "error",
            "exception",
            "syntaxerror",
            "typeerror",
            "valueerror",
            "operationalerror",
            "sqlalchemy.exc",
            "sqlite",
            "failed",
            "no such",
            "duplicate",
            "already exists",
            "not found",
            "can't",
            "cannot",
        ]):
            lines.append(line.rstrip())
    return lines[-120:]


def classify(smoke: Dict[str, Any]) -> List[Dict[str, Any]]:
    errors = smoke.get("errors", [])
    steps = smoke.get("steps", [])
    full_text = "\n".join(errors + [s.get("output", "") for s in steps])
    low = full_text.lower()

    findings: List[Dict[str, Any]] = []

    def add(kind: str, severity: str, reason: str, repair: str) -> None:
        findings.append({
            "kind": kind,
            "severity": severity,
            "reason": reason,
            "repair": repair,
        })

    if "syntaxerror" in low or "invalid syntax" in low:
        add(
            "python_syntax",
            "blocker",
            "Alembic could not import the migration Python file.",
            "Patch migrations/versions/0018_approved_model_migration.py until python -m py_compile and alembic heads both pass.",
        )

    if "typeerror" in low and ("length" in low or "todo" in low):
        add(
            "invalid_sqlalchemy_type_argument",
            "blocker",
            "Generated SQLAlchemy type likely contains placeholder such as length=TODO.",
            "Replace placeholder SQLAlchemy type arguments with safe concrete values, usually sa.String(255), then rerun DB smoke.",
        )

    if "name 'todo' is not defined" in low or "todo" in low and "not defined" in low:
        add(
            "unresolved_todo_symbol",
            "blocker",
            "Generated migration contains executable TODO placeholder.",
            "Convert TODO placeholders into comments and use executable safe defaults.",
        )

    if "jsonb" in low:
        add(
            "sqlite_jsonb_incompatibility",
            "blocker",
            "SQLite does not support PostgreSQL JSONB.",
            "Use sa.JSON() for portable dry-run migration smoke, or branch dialect-specific type later.",
        )

    if "foreign key" in low or "foreignkey" in low:
        add(
            "foreign_key_order_or_target",
            "review",
            "Migration may reference a table not yet present in temp DB.",
            "For smoke, ensure referenced tables are created first or defer FK constraints until full model reconciliation.",
        )

    if "already exists" in low:
        add(
            "duplicate_table_or_constraint",
            "blocker",
            "Migration attempted to create an object that already exists.",
            "Add create-if-missing guards or fix duplicate table list.",
        )

    if "no such table" in low:
        add(
            "missing_table_on_downgrade_or_fk",
            "blocker",
            "Downgrade or FK check referenced a missing table.",
            "Fix downgrade order or remove invalid FK reference from draft.",
        )

    if "not null constraint failed" in low:
        add(
            "not_null_constraint_issue",
            "review",
            "Temp migration or seed path hit NOT NULL constraint.",
            "Confirm nullable/default settings in migration draft.",
        )

    if not findings and errors:
        add(
            "unclassified_smoke_failure",
            "review",
            "Smoke report contains errors but no known classifier matched.",
            "Inspect v12.10.38 step output manually.",
        )

    return findings


def affected_lines() -> List[Dict[str, Any]]:
    text = read(PROMOTED)
    out = []
    for idx, line in enumerate(text.splitlines(), 1):
        low = line.lower()
        if any(k in low for k in ["todo", "jsonb", "foreignkey", "length=todo", "runtimeerror"]):
            out.append({
                "line": idx,
                "text": line.rstrip(),
            })
    return out[:200]


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    smoke = load_json(SMOKE_JSON)
    gate = load_json(GATE_JSON)

    steps = smoke.get("steps", [])
    step_summaries = []
    for step in steps:
        output = step.get("output", "")
        step_summaries.append({
            "step": step.get("step"),
            "returncode": step.get("returncode"),
            "error_lines": extract_error_lines(output),
            "output_tail": output[-3000:],
        })

    findings = classify(smoke)
    affected = affected_lines()

    report = {
        "version": VERSION,
        "generated_at": now(),
        "source_smoke_json": str(SMOKE_JSON),
        "source_gate_json": str(GATE_JSON),
        "promoted_migration": str(PROMOTED),
        "smoke_status": smoke.get("smoke_status"),
        "gate_release_status": gate.get("release_status"),
        "schema_mutation": "none",
        "production_db_touched": smoke.get("production_db_touched"),
        "real_config_upgrade_run": smoke.get("real_config_upgrade_run"),
        "error_count": len(smoke.get("errors", [])),
        "errors": smoke.get("errors", []),
        "findings": findings,
        "affected_lines": affected,
        "step_summaries": step_summaries,
        "next_action": "build v12.10.41 targeted migration repair patch from these findings",
    }

    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True))
    write_md(report)
    write_patch_plan(report)

    print(json.dumps({
        "version": VERSION,
        "smoke_status": report["smoke_status"],
        "gate_release_status": report["gate_release_status"],
        "finding_count": len(findings),
        "affected_line_count": len(affected),
        "schema_mutation": "none",
        "production_db_touched": report["production_db_touched"],
        "real_config_upgrade_run": report["real_config_upgrade_run"],
        "report_json": str(REPORT_JSON),
        "report_md": str(REPORT_MD),
        "patch_plan": str(PATCH_PLAN),
    }, indent=2, sort_keys=True))

    return 0


def write_md(report: Dict[str, Any]) -> None:
    lines = [
        "# v12.10.40 DB Smoke Failure Extractor",
        "",
        f"- **smoke_status**: `{report['smoke_status']}`",
        f"- **gate_release_status**: `{report['gate_release_status']}`",
        "- **schema_mutation**: `none`",
        f"- **production_db_touched**: `{report['production_db_touched']}`",
        f"- **real_config_upgrade_run**: `{report['real_config_upgrade_run']}`",
        f"- **error_count**: `{report['error_count']}`",
        "",
        "## Findings",
        "",
    ]

    if report["findings"]:
        for f in report["findings"]:
            lines.append(f"- **{f['kind']}** / `{f['severity']}` — {f['reason']} Repair: {f['repair']}")
    else:
        lines.append("- none")

    lines.extend(["", "## Smoke errors", ""])

    if report["errors"]:
        for err in report["errors"]:
            lines.append(f"- {err}")
    else:
        lines.append("- none")

    lines.extend(["", "## Affected migration lines", ""])

    if report["affected_lines"]:
        for item in report["affected_lines"]:
            lines.append(f"- line `{item['line']}`: `{item['text']}`")
    else:
        lines.append("- none detected")

    lines.extend(["", "## Step error lines", ""])

    for step in report["step_summaries"]:
        lines.append(f"### {step['step']} returncode={step['returncode']}")
        if step["error_lines"]:
            for line in step["error_lines"]:
                lines.append(f"- `{line}`")
        else:
            lines.append("- no classified error lines")
        lines.append("")

    REPORT_MD.write_text("\n".join(lines))


def write_patch_plan(report: Dict[str, Any]) -> None:
    lines = [
        "# v12.10.40 DB Smoke Repair Targets",
        "",
        "Use this to build v12.10.41. Do not patch blindly.",
        "",
        "## Targeted repairs",
        "",
    ]

    if report["findings"]:
        for f in report["findings"]:
            lines.extend([
                f"### {f['kind']}",
                "",
                f"- severity: `{f['severity']}`",
                f"- reason: {f['reason']}",
                f"- repair: {f['repair']}",
                "",
            ])
    else:
        lines.append("- No automatic repair target detected. Inspect v12.10.38 smoke output manually.")

    lines.extend([
        "",
        "## Safety constraints for v12.10.41",
        "",
        "- Patch only `migrations/versions/0018_approved_model_migration.py` and the draft generator if needed.",
        "- Do not run real DB upgrade.",
        "- Rerun `make report121038` after repair.",
        "- Gate again with `make report121039`.",
    ])

    PATCH_PLAN.write_text("\n".join(lines))


if __name__ == "__main__":
    raise SystemExit(main())
