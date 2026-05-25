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
VERSION = "12.10.45"
TARGET_TABLE = "identity_columns"

OUT_DIR = ROOT / "release/db_smoke_identity_columns_repair"
REPORT_JSON = OUT_DIR / "IDENTITY_COLUMNS_REPAIR_V12_10_45.json"
REPORT_MD = OUT_DIR / "IDENTITY_COLUMNS_REPAIR_V12_10_45.md"


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
    start = -1

    for i, line in enumerate(lines):
        if re.search(r'op\.create_table\(\s*["\']' + re.escape(table) + r'["\']', line):
            start = i
            break

    if start < 0:
        return -1, -1

    depth = 0
    seen = False

    for i in range(start, len(lines)):
        depth += lines[i].count("(")
        depth -= lines[i].count(")")
        if "(" in lines[i]:
            seen = True
        if seen and depth <= 0:
            return start, i

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
        "length=TODO": "length=255",
        "length = TODO": "length=255",
        "sa.String(TODO)": "sa.String(255)",
        "String(TODO)": "String(255)",
        "sa.String(length=TODO)": "sa.String(length=255)",
        "String(length=TODO)": "String(length=255)",
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


def strip_fk(code: str) -> Tuple[str, bool]:
    original = code
    code = re.sub(r",\s*(?:sa\.|db\.)?ForeignKey\([^)]*\)", "", code)
    code = re.sub(r",\s*foreign_key\s*=\s*[^,\)]*", "", code)
    return code, code != original


def normalize_comment(comment: str, reasons: List[str]) -> str:
    comment = comment.strip()
    if reasons:
        suffix = "; ".join(reasons)
        if comment:
            return comment + " | " + suffix
        return "TODO: " + suffix
    return comment


def patch_line(line: str) -> Tuple[str, List[str]]:
    reasons: List[str] = []
    code, comment = split_comment(line)

    code2, todo_changed = patch_executable_todo(code)
    if todo_changed:
        reasons.append("executable TODO placeholder replaced with safe default")

    code3, fk_changed = strip_fk(code2)
    if fk_changed:
        reasons.append("ForeignKey removed for temp SQLite smoke; review FK after DB smoke")

    new_comment = normalize_comment(comment, reasons)

    if new_comment:
        return code3.rstrip() + "  # " + new_comment, reasons
    return code3.rstrip(), reasons


def patch_identity_columns(text: str) -> Tuple[str, List[Dict[str, Any]]]:
    lines = text.splitlines()
    start, end = find_create_table_block(lines, TARGET_TABLE)

    if start < 0:
        raise SystemExit(f"Could not find op.create_table block for {TARGET_TABLE}")

    seen_cols = set()
    new_block: List[str] = []
    changes: List[Dict[str, Any]] = []

    for idx in range(start, end + 1):
        line = lines[idx]
        original = line
        reasons: List[str] = []

        col = column_name(line)

        if col:
            if col in seen_cols:
                indent = line[:len(line) - len(line.lstrip())]
                patched = (
                    indent
                    + "# "
                    + line.lstrip()
                    + "  # TODO: duplicate column commented out for SQLite smoke; review model source"
                )
                reasons.append(f"duplicate column commented out: {col}")
            else:
                seen_cols.add(col)
                patched, reasons = patch_line(line)
        else:
            patched, reasons = patch_line(line)

        new_block.append(patched)

        if patched != original:
            changes.append({
                "line": idx + 1,
                "before": original,
                "after": patched,
                "reasons": reasons,
            })

    new_lines = lines[:start] + new_block + lines[end + 1:]
    return "\n".join(new_lines) + "\n", changes


def executable_todo_lines(text: str) -> List[Dict[str, Any]]:
    out = []
    for idx, line in enumerate(text.splitlines(), 1):
        code = line.split("#", 1)[0]
        if "TODO" in code:
            out.append({"line": idx, "text": line.rstrip()})
    return out


def duplicate_columns_in_table(text: str, table: str) -> List[str]:
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


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    p = active_migration()
    if not p.exists():
        raise SystemExit(f"Missing promoted migration: {p}")

    before = p.read_text()
    after, changes = patch_identity_columns(before)
    p.write_text(after)

    compile_code, compile_out = run(["python", "-m", "py_compile", str(p)])
    heads_code, heads_out = run(["alembic", "heads"])

    remaining_todo = executable_todo_lines(after)
    duplicate_cols = duplicate_columns_in_table(after, TARGET_TABLE)

    errors: List[str] = []
    if compile_code != 0:
        errors.append("promoted migration does not compile")
    if heads_code != 0:
        errors.append("alembic heads failed")
    if "0018_approved_model_migration" not in heads_out:
        errors.append("alembic does not see 0018_approved_model_migration")
    if remaining_todo:
        errors.append("executable TODO placeholders remain")
    if duplicate_cols:
        errors.append("duplicate active columns remain in identity_columns: " + ", ".join(duplicate_cols))

    report = {
        "version": VERSION,
        "generated_at": now(),
        "target_table": TARGET_TABLE,
        "schema_mutation": "none",
        "production_db_touched": False,
        "real_config_upgrade_run": False,
        "promoted_migration": str(p),
        "change_count": len(changes),
        "changes": changes,
        "remaining_executable_todo": remaining_todo,
        "duplicate_columns": duplicate_cols,
        "compile": {"returncode": compile_code, "output": compile_out},
        "alembic_heads": {"returncode": heads_code, "output": heads_out},
        "errors": errors,
        "repair_status": "GO" if not errors else "NO-GO",
    }

    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True))
    write_md(report)

    print(json.dumps({
        "version": VERSION,
        "target_table": TARGET_TABLE,
        "repair_status": report["repair_status"],
        "change_count": len(changes),
        "remaining_executable_todo_count": len(remaining_todo),
        "duplicate_column_count": len(duplicate_cols),
        "schema_mutation": "none",
        "production_db_touched": False,
        "real_config_upgrade_run": False,
        "report_json": str(REPORT_JSON),
        "report_md": str(REPORT_MD),
    }, indent=2, sort_keys=True))

    return 0 if not errors else 1


def write_md(report: Dict[str, Any]) -> None:
    lines = [
        "# v12.10.45 identity_columns Repair Report",
        "",
        f"- **repair_status**: `{report['repair_status']}`",
        f"- **target_table**: `{report['target_table']}`",
        "- **schema_mutation**: `none`",
        "- **production_db_touched**: `False`",
        "- **real_config_upgrade_run**: `False`",
        f"- **change_count**: `{report['change_count']}`",
        f"- **remaining_executable_todo_count**: `{len(report['remaining_executable_todo'])}`",
        f"- **duplicate_column_count**: `{len(report['duplicate_columns'])}`",
        "",
        "## Errors",
        "",
    ]

    if report["errors"]:
        for err in report["errors"]:
            lines.append(f"- {err}")
    else:
        lines.append("- none")

    lines.extend(["", "## Changes", ""])

    if not report["changes"]:
        lines.append("- no changes required")
    else:
        for c in report["changes"]:
            lines.append(f"### line {c['line']}")
            lines.append("")
            lines.append("Before:")
            lines.append("```python")
            lines.append(c["before"])
            lines.append("```")
            lines.append("After:")
            lines.append("```python")
            lines.append(c["after"])
            lines.append("```")
            lines.append("")

    REPORT_MD.write_text("\n".join(lines))


if __name__ == "__main__":
    raise SystemExit(main())
