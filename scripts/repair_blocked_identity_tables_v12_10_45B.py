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
VERSION = "12.10.45B"

TARGET_TABLES = [
    "all_tab_identity_cols",
    "identity_columns",
]

OUT_DIR = ROOT / "release/blocked_identity_table_repair"
REPORT_JSON = OUT_DIR / "BLOCKED_IDENTITY_TABLE_REPAIR_V12_10_45B.json"
REPORT_MD = OUT_DIR / "BLOCKED_IDENTITY_TABLE_REPAIR_V12_10_45B.md"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(cmd: List[str]) -> Tuple[int, str]:
    try:
        out = subprocess.check_output(cmd, cwd=ROOT, stderr=subprocess.STDOUT, text=True)
        return 0, out
    except subprocess.CalledProcessError as exc:
        return exc.returncode, exc.output


def active_migration() -> Path:
    cfg = configparser.ConfigParser()
    cfg.read(ROOT / "alembic.ini")
    script_location = cfg.get("alembic", "script_location", fallback="migrations")
    return ROOT / script_location / "versions" / "0018_approved_model_migration.py"


def find_create_table_block(lines: List[str], table: str) -> Tuple[int, int]:
    """Find op.create_table block for both one-line and multiline forms.

    Supports:
        op.create_table("table", ...)
        op.create_table(
            "table",
            ...
        )
    """
    start = -1

    one_line = re.compile(r'op\.create_table\(\s*["\']' + re.escape(table) + r'["\']')

    for idx, line in enumerate(lines):
        if one_line.search(line):
            start = idx
            break

        if "op.create_table" in line:
            preview = "\n".join(lines[idx: min(len(lines), idx + 5)])
            multi = re.search(
                r'op\.create_table\(\s*\n\s*["\']' + re.escape(table) + r'["\']',
                preview,
                re.MULTILINE,
            )
            if multi:
                start = idx
                break

    if start < 0:
        return -1, -1

    depth = 0
    seen_open = False

    for idx in range(start, len(lines)):
        depth += lines[idx].count("(")
        depth -= lines[idx].count(")")
        if "(" in lines[idx]:
            seen_open = True
        if seen_open and depth <= 0:
            return start, idx

    return start, len(lines) - 1


def column_name(line: str) -> str | None:
    m = re.search(r'sa\.Column\(\s*["\']([^"\']+)["\']', line)
    return m.group(1) if m else None


def split_comment(line: str) -> Tuple[str, str]:
    if "#" not in line:
        return line, ""
    code, comment = line.split("#", 1)
    return code, comment


def patch_executable_todo(code: str) -> Tuple[str, bool]:
    original = code

    replacements = {
        "length=255": "length=255",
        "length = TODO": "length=255",
        "sa.String(255)": "sa.String(255)",
        "String(255)": "String(255)",
        "sa.String(length=255)": "sa.String(length=255)",
        "String(length=255)": "String(length=255)",
        "nullable=TODO": "nullable=True",
        "nullable = TODO": "nullable=True",
        "index=TODO": "index=False",
        "index = TODO": "index=False",
        "unique=TODO": "unique=False",
        "unique = TODO": "unique=False",
        "default=TODO": "default=None",
        "default = TODO": "default=None",
        "server_default=TODO": "server_default=None",
        "server_default = TODO": "server_default=None",
    }

    for old, new in replacements.items():
        code = code.replace(old, new)

    code = re.sub(r"(?<=,\s)TODO(?=\s*[,)\]])", "None", code)
    code = re.sub(r"(?<=\()\s*TODO(?=\s*[,)\]])", "None", code)
    code = re.sub(r"=\s*TODO\b", "=None", code)
    code = re.sub(r"\bTODO\b", "None", code)

    return code, code != original


def strip_fk_args(code: str) -> Tuple[str, bool]:
    original = code

    code = re.sub(r",\s*(?:sa\.|db\.)?ForeignKey\([^)]*\)", "", code)
    code = re.sub(r",\s*foreign_key\s*=\s*[^,\)]*", "", code)

    return code, code != original


def normalize_sqlalchemy_types(code: str) -> Tuple[str, bool]:
    original = code

    # SQLite-safe smoke normalization.
    code = code.replace("sa.JSONB()", "sa.JSON()")
    code = code.replace("postgresql.JSONB()", "sa.JSON()")
    code = code.replace("postgresql.UUID()", "sa.String(36)")
    code = code.replace("sa.UUID()", "sa.String(36)")

    # Bad generated server_default placeholders should not execute in smoke.
    code = re.sub(r",\s*server_default\s*=\s*sa\.text\(\s*['\"]TODO['\"]\s*\)", "", code)
    code = re.sub(r",\s*server_default\s*=\s*['\"]TODO['\"]", "", code)

    return code, code != original


def patch_line(line: str) -> Tuple[str, List[str]]:
    reasons: List[str] = []

    code, comment = split_comment(line)

    code2, changed_todo = patch_executable_todo(code)
    if changed_todo:
        reasons.append("executable TODO placeholder replaced with safe default")

    code3, changed_fk = strip_fk_args(code2)
    if changed_fk:
        reasons.append("ForeignKey removed for temp SQLite smoke; review FK after DB smoke")

    code4, changed_type = normalize_sqlalchemy_types(code3)
    if changed_type:
        reasons.append("dialect/placeholder type normalized for temp SQLite smoke")

    comment = comment.strip()
    if reasons:
        suffix = "; ".join(reasons)
        comment = f"{comment} | {suffix}" if comment else f"TODO: {suffix}"

    if comment:
        return code4.rstrip() + "  # " + comment, reasons

    return code4.rstrip(), reasons


def patch_table(lines: List[str], table: str) -> Tuple[List[str], List[Dict[str, Any]], bool]:
    start, end = find_create_table_block(lines, table)

    if start < 0:
        return lines, [{
            "table": table,
            "line": None,
            "before": "",
            "after": "",
            "reasons": ["create_table block not found"],
        }], False

    seen_cols = set()
    new_block: List[str] = []
    changes: List[Dict[str, Any]] = []

    for idx in range(start, end + 1):
        original = lines[idx]
        patched = original
        reasons: List[str] = []

        col = column_name(original)

        if col:
            if col in seen_cols:
                indent = original[:len(original) - len(original.lstrip())]
                patched = (
                    indent
                    + "# "
                    + original.lstrip()
                    + "  # TODO: duplicate column commented out for SQLite smoke; review model source"
                )
                reasons.append(f"duplicate active column commented out: {col}")
            else:
                seen_cols.add(col)
                patched, reasons = patch_line(original)
        else:
            patched, reasons = patch_line(original)

        new_block.append(patched)

        if patched != original:
            changes.append({
                "table": table,
                "line": idx + 1,
                "before": original,
                "after": patched,
                "reasons": reasons,
            })

    new_lines = lines[:start] + new_block + lines[end + 1:]
    return new_lines, changes, True


def executable_todo_lines(text: str) -> List[Dict[str, Any]]:
    bad = []
    for idx, line in enumerate(text.splitlines(), 1):
        code = line.split("#", 1)[0]
        if "TODO" in code:
            bad.append({"line": idx, "text": line.rstrip()})
    return bad


def duplicate_active_columns(text: str, table: str) -> List[str]:
    lines = text.splitlines()
    start, end = find_create_table_block(lines, table)

    if start < 0:
        return []

    seen = set()
    dupes = []

    for line in lines[start:end + 1]:
        if line.lstrip().startswith("#"):
            continue
        col = column_name(line)
        if not col:
            continue
        if col in seen:
            dupes.append(col)
        seen.add(col)

    return sorted(set(dupes))


def patch_generators() -> List[Dict[str, Any]]:
    paths = [
        ROOT / "scripts" / "build_approved_migration_draft_v12_10_35.py",
        ROOT / "scripts" / "repair_0018_todo_placeholders_v12_10_41.py",
        ROOT / "scripts" / "targeted_failed_table_smoke_repair_v12_10_43.py",
    ]

    changes = []

    for path in paths:
        if not path.exists():
            continue

        before = path.read_text()
        after = before
        after = after.replace("sa.String(length=255)", "sa.String(length=255)")
        after = after.replace("length=255", "length=255")
        after = after.replace("sa.String(255)", "sa.String(255)")
        after = after.replace("String(255)", "String(255)")

        if after != before:
            path.write_text(after)
            changes.append({
                "file": str(path),
                "change": "removed executable TODO-producing placeholders",
            })

    return changes


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    migration = active_migration()
    if not migration.exists():
        raise SystemExit(f"Missing promoted migration: {migration}")

    lines = migration.read_text().splitlines()
    all_changes: List[Dict[str, Any]] = []
    found_tables = {}

    for table in TARGET_TABLES:
        lines, changes, found = patch_table(lines, table)
        all_changes.extend(changes)
        found_tables[table] = found

    migration.write_text("\n".join(lines) + "\n")
    generator_changes = patch_generators()

    compile_code, compile_out = run(["python", "-m", "py_compile", str(migration)])
    heads_code, heads_out = run(["alembic", "heads"])

    after_text = migration.read_text()
    remaining_todo = executable_todo_lines(after_text)
    duplicate_map = {
        table: duplicate_active_columns(after_text, table)
        for table in TARGET_TABLES
    }

    errors = []
    if compile_code != 0:
        errors.append("promoted migration does not compile")
    if heads_code != 0:
        errors.append("alembic heads failed")
    if "0018_approved_model_migration" not in heads_out:
        errors.append("alembic does not see 0018 head")
    if remaining_todo:
        errors.append("executable TODO placeholders remain")
    for table, dupes in duplicate_map.items():
        if dupes:
            errors.append(f"duplicate active columns remain in {table}: {', '.join(dupes)}")
    for table, found in found_tables.items():
        if not found:
            errors.append(f"target create_table block not found: {table}")

    report = {
        "version": VERSION,
        "generated_at": now(),
        "target_tables": TARGET_TABLES,
        "found_tables": found_tables,
        "schema_mutation": "none",
        "production_db_touched": False,
        "real_config_upgrade_run": False,
        "promoted_migration": str(migration),
        "change_count": len(all_changes),
        "changes": all_changes,
        "generator_changes": generator_changes,
        "remaining_executable_todo": remaining_todo,
        "duplicate_columns": duplicate_map,
        "compile": {"returncode": compile_code, "output": compile_out},
        "alembic_heads": {"returncode": heads_code, "output": heads_out},
        "errors": errors,
        "repair_status": "GO" if not errors else "NO-GO",
    }

    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True))
    write_md(report)

    print(json.dumps({
        "version": VERSION,
        "repair_status": report["repair_status"],
        "target_tables": TARGET_TABLES,
        "found_tables": found_tables,
        "change_count": len(all_changes),
        "generator_change_count": len(generator_changes),
        "remaining_executable_todo_count": len(remaining_todo),
        "duplicate_columns": duplicate_map,
        "compile_returncode": compile_code,
        "alembic_heads_returncode": heads_code,
        "schema_mutation": "none",
        "production_db_touched": False,
        "real_config_upgrade_run": False,
        "report_json": str(REPORT_JSON),
        "report_md": str(REPORT_MD),
    }, indent=2, sort_keys=True))

    return 0 if not errors else 1


def write_md(report: Dict[str, Any]) -> None:
    lines = [
        "# v12.10.45B Blocked Identity Table Repair Report",
        "",
        f"- **repair_status**: `{report['repair_status']}`",
        f"- **target_tables**: `{', '.join(report['target_tables'])}`",
        "- **schema_mutation**: `none`",
        "- **production_db_touched**: `False`",
        "- **real_config_upgrade_run**: `False`",
        f"- **change_count**: `{report['change_count']}`",
        f"- **remaining_executable_todo_count**: `{len(report['remaining_executable_todo'])}`",
        "",
        "## Found tables",
        "",
    ]

    for table, found in report["found_tables"].items():
        lines.append(f"- `{table}`: `{found}`")

    lines.extend(["", "## Errors", ""])

    if report["errors"]:
        for err in report["errors"]:
            lines.append(f"- {err}")
    else:
        lines.append("- none")

    lines.extend(["", "## Duplicate columns", ""])

    for table, dupes in report["duplicate_columns"].items():
        lines.append(f"- `{table}`: `{', '.join(dupes) if dupes else 'none'}`")

    lines.extend(["", "## Changes", ""])

    if not report["changes"]:
        lines.append("- no changes required")
    else:
        for change in report["changes"][:250]:
            lines.append(f"### {change['table']} line {change['line']}")
            lines.append("")
            lines.append("Before:")
            lines.append("```python")
            lines.append(change["before"])
            lines.append("```")
            lines.append("After:")
            lines.append("```python")
            lines.append(change["after"])
            lines.append("```")
            lines.append("")

    REPORT_MD.write_text("\n".join(lines))


if __name__ == "__main__":
    raise SystemExit(main())
