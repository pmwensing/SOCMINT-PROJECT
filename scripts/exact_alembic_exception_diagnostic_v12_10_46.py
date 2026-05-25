#!/usr/bin/env python3
from __future__ import annotations

import configparser
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


ROOT = Path.cwd()
VERSION = "12.10.46"

SMOKE_JSON = ROOT / "release/db_migration_smoke/DB_MIGRATION_SMOKE_V12_10_38.json"
FULL_OUTPUT = ROOT / "release/db_smoke_exact_failure/FAILING_UPGRADE_OUTPUT_V12_10_42.txt"
LOCATOR_JSON = ROOT / "release/db_smoke_exact_failure/DB_SMOKE_EXACT_FAILURE_LOCATOR_V12_10_42.json"

OUT_DIR = ROOT / "release/exact_alembic_exception"
REPORT_JSON = OUT_DIR / "EXACT_ALEMBIC_EXCEPTION_DIAGNOSTIC_V12_10_46.json"
REPORT_MD = OUT_DIR / "EXACT_ALEMBIC_EXCEPTION_DIAGNOSTIC_V12_10_46.md"
IDENTITY_BLOCKS_MD = OUT_DIR / "IDENTITY_TABLE_BLOCKS_V12_10_46.md"
REPAIR_HINTS_MD = OUT_DIR / "IDENTITY_REPAIR_HINTS_V12_10_46.md"

TARGET_TABLES = ["all_tab_identity_cols", "identity_columns"]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read(path: Path) -> str:
    try:
        return path.read_text(errors="replace")
    except Exception:
        return ""


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def active_migration() -> Path:
    cfg = configparser.ConfigParser()
    cfg.read(ROOT / "alembic.ini")
    script_location = cfg.get("alembic", "script_location", fallback="migrations")
    return ROOT / script_location / "versions" / "0018_approved_model_migration.py"


def find_create_table_block(text: str, table: str) -> Tuple[int, int, str]:
    lines = text.splitlines()
    start = -1

    for i, line in enumerate(lines):
        if "op.create_table" not in line:
            continue

        preview = "\n".join(lines[i:i + 6])
        if re.search(
            r'op\.create_table\(\s*(?:\n\s*)?["\']' + re.escape(table) + r'["\']',
            preview,
            re.MULTILINE,
        ):
            start = i
            break

    if start < 0:
        return -1, -1, ""

    depth = 0
    seen = False
    end = start

    for i in range(start, len(lines)):
        depth += lines[i].count("(")
        depth -= lines[i].count(")")
        if "(" in lines[i]:
            seen = True
        end = i
        if seen and depth <= 0:
            break

    block = "\n".join(f"{idx + 1:04d}: {lines[idx]}" for idx in range(start, end + 1))
    return start + 1, end + 1, block


def extract_exception_lines(output: str) -> List[str]:
    lines = output.splitlines()
    important = []

    patterns = [
        "Traceback",
        "Error:",
        "Exception",
        "sqlalchemy.exc",
        "OperationalError",
        "CompileError",
        "ArgumentError",
        "TypeError",
        "ValueError",
        "NameError",
        "SyntaxError",
        "IntegrityError",
        "Duplicate",
        "duplicate",
        "already exists",
        "no such",
        "near ",
        "sqlite3.",
        "FAILED",
        "failed",
    ]

    for line in lines:
        if any(p in line for p in patterns):
            important.append(line.rstrip())

    return important[-120:]


def last_traceback(output: str) -> str:
    idx = output.rfind("Traceback (most recent call last):")
    if idx < 0:
        return output[-5000:]
    return output[idx:][-10000:]


def classify_exact(output: str, blocks: Dict[str, Dict[str, Any]]) -> List[Dict[str, str]]:
    low = output.lower()
    findings: List[Dict[str, str]] = []

    def add(kind: str, severity: str, repair: str) -> None:
        findings.append({"kind": kind, "severity": severity, "repair": repair})

    if "multiple primary keys" in low or "more than one primary key" in low:
        add("multiple_primary_keys", "blocker", "Remove/comment extra primary_key=True in the failing table block; keep one PK only.")

    if "duplicate column name" in low:
        add("duplicate_column_name", "blocker", "Comment duplicate column definitions in the failing table block.")

    if "default value of column" in low or "server_default" in low and "syntax" in low:
        add("invalid_server_default", "blocker", "Remove unsafe server_default/default expressions for SQLite smoke.")

    if "near" in low and "syntax error" in low:
        add("sqlite_syntax_error", "blocker", "Patch the exact failing column/constraint shown in traceback or SQL output.")

    if "foreign key" in low:
        add("foreign_key_issue", "review", "Remove/defer FK constraints for temp SQLite smoke, then review for production migration.")

    if "not a valid" in low or "argumenterror" in low:
        add("invalid_sqlalchemy_argument", "blocker", "Fix invalid SQLAlchemy Column/type/constraint arguments in the failing table block.")

    if "typeerror" in low:
        add("python_type_error", "blocker", "Fix invalid generated Python call arguments in the failing table block.")

    if "nameerror" in low or "not defined" in low:
        add("undefined_symbol", "blocker", "Replace unresolved executable symbol with safe literal/type and keep TODO as comment.")

    for table, info in blocks.items():
        block = info.get("block", "")
        active_pk = len(re.findall(r"primary_key\s*=\s*True", strip_commented_lines(block)))
        if active_pk > 1:
            add(f"{table}_multiple_active_primary_keys", "blocker", f"`{table}` has {active_pk} active primary_key=True columns; keep one only.")

        server_defaults = re.findall(r"server_default\s*=", strip_commented_lines(block))
        if server_defaults:
            add(f"{table}_server_defaults_present", "review", f"`{table}` has server_default expressions; remove for SQLite smoke if traceback points there.")

    if not findings:
        add("unclassified_exact_failure", "review", "Inspect failing output and identity table blocks manually; no known classifier matched.")

    # Deduplicate.
    seen = set()
    out = []
    for f in findings:
        key = (f["kind"], f["repair"])
        if key not in seen:
            seen.add(key)
            out.append(f)
    return out


def strip_commented_lines(block: str) -> str:
    return "\n".join(
        line for line in block.splitlines()
        if not line.split(":", 1)[-1].lstrip().startswith("#")
    )


def table_pattern_scan(block: str) -> Dict[str, Any]:
    active = strip_commented_lines(block)

    columns = re.findall(r'sa\.Column\(\s*["\']([^"\']+)["\']', active)

    dupes = sorted({c for c in columns if columns.count(c) > 1})

    pk_lines = []
    server_default_lines = []
    default_lines = []
    fk_lines = []
    unsupported_lines = []

    for line in active.splitlines():
        if "primary_key=True" in line or "primary_key = True" in line:
            pk_lines.append(line)
        if "server_default" in line:
            server_default_lines.append(line)
        if re.search(r"\bdefault\s*=", line):
            default_lines.append(line)
        if "ForeignKey" in line:
            fk_lines.append(line)
        if any(x in line for x in ["JSONB", "postgresql.", "UUID()", "ARRAY", "Enum("]):
            unsupported_lines.append(line)

    return {
        "column_count": len(columns),
        "columns": columns,
        "duplicate_columns": dupes,
        "primary_key_count": len(pk_lines),
        "primary_key_lines": pk_lines,
        "server_default_count": len(server_default_lines),
        "server_default_lines": server_default_lines,
        "default_count": len(default_lines),
        "default_lines": default_lines,
        "foreign_key_count": len(fk_lines),
        "foreign_key_lines": fk_lines,
        "unsupported_dialect_line_count": len(unsupported_lines),
        "unsupported_dialect_lines": unsupported_lines,
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    smoke = load_json(SMOKE_JSON)
    locator = load_json(LOCATOR_JSON)
    migration = active_migration()
    migration_text = read(migration)

    output = read(FULL_OUTPUT)
    if not output:
        # Fall back to embedded smoke step output.
        for step in smoke.get("steps", []):
            if step.get("step") == "upgrade_head_temp_sqlite":
                output = step.get("output", "")

    blocks: Dict[str, Dict[str, Any]] = {}
    for table in TARGET_TABLES:
        start, end, block = find_create_table_block(migration_text, table)
        blocks[table] = {
            "start_line": start,
            "end_line": end,
            "found": bool(block),
            "block": block,
            "scan": table_pattern_scan(block) if block else {},
        }

    exception_lines = extract_exception_lines(output)
    traceback = last_traceback(output)
    findings = classify_exact(output, blocks)

    report = {
        "version": VERSION,
        "generated_at": now(),
        "schema_mutation": "none",
        "production_db_touched": smoke.get("production_db_touched"),
        "real_config_upgrade_run": smoke.get("real_config_upgrade_run"),
        "smoke_status": smoke.get("smoke_status"),
        "version_after_upgrade": smoke.get("version_after_upgrade"),
        "probable_failing_table": locator.get("probable_failing_table"),
        "missing_after_upgrade": smoke.get("missing_after_upgrade", []),
        "lingering_after_downgrade": smoke.get("lingering_after_downgrade", []),
        "full_output_path": str(FULL_OUTPUT),
        "promoted_migration": str(migration),
        "exception_lines": exception_lines,
        "last_traceback": traceback,
        "target_blocks": blocks,
        "findings": findings,
        "next_action": "build v12.10.47 exact identity block repair based on these findings",
    }

    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True))
    write_report(report)
    write_blocks(report)
    write_hints(report)

    print(json.dumps({
        "version": VERSION,
        "smoke_status": report["smoke_status"],
        "probable_failing_table": report["probable_failing_table"],
        "finding_count": len(findings),
        "exception_line_count": len(exception_lines),
        "all_tab_identity_cols_found": blocks["all_tab_identity_cols"]["found"],
        "identity_columns_found": blocks["identity_columns"]["found"],
        "all_tab_identity_cols_pk_count": blocks["all_tab_identity_cols"]["scan"].get("primary_key_count"),
        "identity_columns_pk_count": blocks["identity_columns"]["scan"].get("primary_key_count"),
        "schema_mutation": "none",
        "production_db_touched": report["production_db_touched"],
        "real_config_upgrade_run": report["real_config_upgrade_run"],
        "report_json": str(REPORT_JSON),
        "report_md": str(REPORT_MD),
        "identity_blocks": str(IDENTITY_BLOCKS_MD),
        "repair_hints": str(REPAIR_HINTS_MD),
    }, indent=2, sort_keys=True))

    return 0


def write_report(report: Dict[str, Any]) -> None:
    lines = [
        "# v12.10.46 Exact Alembic Exception Diagnostic",
        "",
        f"- **smoke_status**: `{report['smoke_status']}`",
        f"- **probable_failing_table**: `{report['probable_failing_table']}`",
        "- **schema_mutation**: `none`",
        f"- **production_db_touched**: `{report['production_db_touched']}`",
        f"- **real_config_upgrade_run**: `{report['real_config_upgrade_run']}`",
        f"- **version_after_upgrade**: `{report['version_after_upgrade']}`",
        f"- **missing_after_upgrade**: `{len(report['missing_after_upgrade'])}`",
        f"- **lingering_after_downgrade**: `{len(report['lingering_after_downgrade'])}`",
        "",
        "## Findings",
        "",
    ]

    for finding in report["findings"]:
        lines.append(f"- **{finding['kind']}** / `{finding['severity']}` — {finding['repair']}")

    lines.extend(["", "## Exception lines", ""])

    if report["exception_lines"]:
        for line in report["exception_lines"]:
            lines.append(f"- `{line}`")
    else:
        lines.append("- none extracted")

    lines.extend(["", "## Last traceback/output tail", "", "```text", report["last_traceback"], "```"])

    REPORT_MD.write_text("\n".join(lines))


def write_blocks(report: Dict[str, Any]) -> None:
    lines = [
        "# v12.10.46 Identity Table Blocks",
        "",
    ]

    for table, info in report["target_blocks"].items():
        scan = info.get("scan", {})
        lines.extend([
            f"## `{table}`",
            "",
            f"- found: `{info['found']}`",
            f"- start_line: `{info['start_line']}`",
            f"- end_line: `{info['end_line']}`",
            f"- column_count: `{scan.get('column_count')}`",
            f"- primary_key_count: `{scan.get('primary_key_count')}`",
            f"- duplicate_columns: `{', '.join(scan.get('duplicate_columns', [])) if scan.get('duplicate_columns') else 'none'}`",
            f"- server_default_count: `{scan.get('server_default_count')}`",
            f"- foreign_key_count: `{scan.get('foreign_key_count')}`",
            f"- unsupported_dialect_line_count: `{scan.get('unsupported_dialect_line_count')}`",
            "",
            "```python",
            info.get("block", ""),
            "```",
            "",
        ])

    IDENTITY_BLOCKS_MD.write_text("\n".join(lines))


def write_hints(report: Dict[str, Any]) -> None:
    lines = [
        "# v12.10.46 Identity Repair Hints",
        "",
        "Use this for v12.10.47. Do not patch blindly.",
        "",
        "## Findings",
        "",
    ]

    for finding in report["findings"]:
        lines.extend([
            f"### {finding['kind']}",
            "",
            f"- severity: `{finding['severity']}`",
            f"- repair: {finding['repair']}",
            "",
        ])

    lines.extend([
        "## Next repair constraints",
        "",
        "- Patch only `migrations/versions/0018_approved_model_migration.py` unless generator source clearly caused the issue.",
        "- Keep TODO text as comments only.",
        "- Do not run real DB upgrade.",
        "- Rerun v12.10.38 and v12.10.39 after repair.",
    ])

    REPAIR_HINTS_MD.write_text("\n".join(lines))


if __name__ == "__main__":
    raise SystemExit(main())
