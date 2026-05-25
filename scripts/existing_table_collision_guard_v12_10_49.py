#!/usr/bin/env python3
from __future__ import annotations

import configparser
import json
import os
import re
import sqlite3
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


ROOT = Path.cwd()
VERSION = "12.10.49"
BASE_REV = "0017_v12_10_schema_reconciliation"
HEAD_REV = "0018_approved_model_migration"

OUT_DIR = ROOT / "release/existing_table_collision_guard"
REPORT_JSON = OUT_DIR / "EXISTING_TABLE_COLLISION_GUARD_V12_10_49.json"
REPORT_MD = OUT_DIR / "EXISTING_TABLE_COLLISION_GUARD_V12_10_49.md"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(cmd: List[str], env: Dict[str, str] | None = None) -> Tuple[int, str]:
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        env=env or os.environ.copy(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return proc.returncode, proc.stdout


def active_versions_dir() -> Path:
    cfg = configparser.ConfigParser()
    cfg.read(ROOT / "alembic.ini")
    script_location = cfg.get("alembic", "script_location", fallback="migrations")
    return ROOT / script_location / "versions"


def migration_path() -> Path:
    return active_versions_dir() / "0018_approved_model_migration.py"


def sqlite_tables(db_path: Path) -> List[str]:
    if not db_path.exists():
        return []
    con = sqlite3.connect(str(db_path))
    try:
        rows = con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
        return [r[0] for r in rows]
    finally:
        con.close()


def make_temp_alembic_config(tmp_dir: Path, db_url: str) -> Path:
    src = ROOT / "alembic.ini"
    cfg = configparser.ConfigParser()
    cfg.read(src)

    if not cfg.has_section("alembic"):
        cfg.add_section("alembic")

    script_location = cfg.get("alembic", "script_location", fallback="migrations")
    cfg.set("alembic", "script_location", str((ROOT / script_location).resolve()))
    cfg.set("alembic", "sqlalchemy.url", db_url)

    dst = tmp_dir / "alembic_v12_10_49.ini"
    with dst.open("w") as f:
        cfg.write(f)

    return dst


def temp_env(db_url: str) -> Dict[str, str]:
    env = os.environ.copy()
    for key in [
        "DATABASE_URL",
        "SQLALCHEMY_DATABASE_URI",
        "SOCMINT_DATABASE_URL",
        "SOCMINT_DB_URL",
        "POSTGRES_URL",
        "DATABASE_URI",
        "APP_DATABASE_URL",
    ]:
        env[key] = db_url

    env["V12_10_49_COLLISION_GUARD"] = "1"
    env["SOCMINT_LOG_FILE"] = str((OUT_DIR / "collision_guard_socmint.log").resolve())
    return env


def baseline_0017_tables() -> Dict[str, Any]:
    tmp_root = Path(tempfile.mkdtemp(prefix="socmint_v12_10_49_base_"))
    db_path = tmp_root / "baseline_0017.sqlite"
    db_url = f"sqlite:///{db_path}"
    cfg = make_temp_alembic_config(tmp_root, db_url)
    env = temp_env(db_url)

    code, out = run(["alembic", "-c", str(cfg), "upgrade", BASE_REV], env)
    tables = sqlite_tables(db_path)

    return {
        "tmp_root": str(tmp_root),
        "db_path": str(db_path),
        "config": str(cfg),
        "returncode": code,
        "output": out,
        "tables": tables,
    }


def extract_create_tables(text: str) -> List[str]:
    return re.findall(r'op\.create_table\(\s*(?:\n\s*)?["\']([^"\']+)["\']', text, re.MULTILINE)


def extract_drop_tables(text: str) -> List[str]:
    return re.findall(r'op\.drop_table\(\s*["\']([^"\']+)["\']', text)


def find_create_block(lines: List[str], table: str) -> Tuple[int, int]:
    start = -1
    for idx, line in enumerate(lines):
        if "op.create_table" not in line:
            continue
        preview = "\n".join(lines[idx:idx + 8])
        if re.search(
            r'op\.create_table\(\s*(?:\n\s*)?["\']' + re.escape(table) + r'["\']',
            preview,
            re.MULTILINE,
        ):
            start = idx
            break

    if start < 0:
        return -1, -1

    depth = 0
    seen = False
    for idx in range(start, len(lines)):
        depth += lines[idx].count("(")
        depth -= lines[idx].count(")")
        if "(" in lines[idx]:
            seen = True
        if seen and depth <= 0:
            return start, idx

    return start, len(lines) - 1


def comment_block(lines: List[str], start: int, end: int, note: str) -> Tuple[List[str], List[Dict[str, Any]]]:
    changes = []
    new_lines = lines[:]

    for idx in range(start, end + 1):
        line = new_lines[idx]
        if line.lstrip().startswith("#"):
            continue

        indent = line[:len(line) - len(line.lstrip())]
        patched = indent + "# " + line.lstrip() + f"  # TODO: {note}"

        new_lines[idx] = patched
        changes.append({
            "line": idx + 1,
            "before": line,
            "after": patched,
            "reason": note,
        })

    return new_lines, changes


def comment_drop_line(lines: List[str], table: str) -> Tuple[List[str], List[Dict[str, Any]]]:
    changes = []
    new_lines = lines[:]
    pattern = re.compile(r'op\.drop_table\(\s*["\']' + re.escape(table) + r'["\']')

    for idx, line in enumerate(new_lines):
        if not pattern.search(line):
            continue
        if line.lstrip().startswith("#"):
            continue

        indent = line[:len(line) - len(line.lstrip())]
        patched = (
            indent
            + "# "
            + line.lstrip()
            + "  # TODO: collision table existed before 0018; downgrade must not drop baseline table"
        )
        new_lines[idx] = patched
        changes.append({
            "line": idx + 1,
            "before": line,
            "after": patched,
            "reason": "collision table existed before 0018; drop neutralized",
        })

    return new_lines, changes


def patch_collision_tables(collision_tables: List[str]) -> Dict[str, Any]:
    p = migration_path()
    if not p.exists():
        raise SystemExit(f"Missing promoted migration: {p}")

    original = p.read_text()
    lines = original.splitlines()
    all_changes = []
    not_found = []

    for table in collision_tables:
        start, end = find_create_block(lines, table)
        if start < 0:
            not_found.append(table)
            continue

        lines, changes = comment_block(
            lines,
            start,
            end,
            f"create_table neutralized: `{table}` already exists at {BASE_REV}; review original schema ownership",
        )
        all_changes.extend([{**c, "table": table, "kind": "create_block"} for c in changes])

        lines, drop_changes = comment_drop_line(lines, table)
        all_changes.extend([{**c, "table": table, "kind": "drop_line"} for c in drop_changes])

    p.write_text("\n".join(lines) + "\n")

    return {
        "promoted_migration": str(p),
        "collision_tables": collision_tables,
        "not_found": not_found,
        "change_count": len(all_changes),
        "changes": all_changes,
    }


def validate_python_and_head() -> Dict[str, Any]:
    p = migration_path()
    py_code, py_out = run(["python", "-m", "py_compile", str(p)])
    heads_code, heads_out = run(["alembic", "heads"])

    return {
        "py_compile": {"returncode": py_code, "output": py_out},
        "alembic_heads": {"returncode": heads_code, "output": heads_out},
        "ok": py_code == 0 and heads_code == 0 and HEAD_REV in heads_out,
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    baseline = baseline_0017_tables()
    if baseline["returncode"] != 0:
        raise SystemExit("Could not build temp 0017 baseline:\n" + baseline["output"])

    p = migration_path()
    text = p.read_text()

    create_tables = extract_create_tables(text)
    drop_tables = extract_drop_tables(text)

    baseline_set = set(baseline["tables"])
    create_set = set(create_tables)

    collision_tables = sorted(create_set & baseline_set)

    patch = patch_collision_tables(collision_tables) if collision_tables else {
        "promoted_migration": str(p),
        "collision_tables": [],
        "not_found": [],
        "change_count": 0,
        "changes": [],
    }

    validation = validate_python_and_head()

    errors = []
    if not validation["ok"]:
        errors.append("promoted migration failed compile/head validation")
    if patch["not_found"]:
        errors.append("collision tables not found in promoted migration: " + ", ".join(patch["not_found"]))

    report = {
        "version": VERSION,
        "generated_at": now(),
        "schema_mutation": "none",
        "production_db_touched": False,
        "real_config_upgrade_run": False,
        "baseline_revision": BASE_REV,
        "head_revision": HEAD_REV,
        "baseline_table_count": len(baseline["tables"]),
        "baseline_tables": baseline["tables"],
        "create_table_count_before_patch": len(create_tables),
        "drop_table_count_before_patch": len(drop_tables),
        "create_tables_before_patch": create_tables,
        "drop_tables_before_patch": drop_tables,
        "collision_table_count": len(collision_tables),
        "collision_tables": collision_tables,
        "patch": patch,
        "validation": validation,
        "errors": errors,
        "guard_status": "GO" if not errors else "NO-GO",
    }

    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True))
    write_md(report)

    print(json.dumps({
        "version": VERSION,
        "guard_status": report["guard_status"],
        "collision_table_count": len(collision_tables),
        "collision_tables": collision_tables,
        "change_count": patch["change_count"],
        "schema_mutation": "none",
        "production_db_touched": False,
        "real_config_upgrade_run": False,
        "report_json": str(REPORT_JSON),
        "report_md": str(REPORT_MD),
    }, indent=2, sort_keys=True))

    return 0 if not errors else 1


def write_md(report: Dict[str, Any]) -> None:
    lines = [
        "# v12.10.49 Existing Table Collision Guard",
        "",
        f"- **guard_status**: `{report['guard_status']}`",
        f"- **baseline_revision**: `{report['baseline_revision']}`",
        f"- **head_revision**: `{report['head_revision']}`",
        "- **schema_mutation**: `none`",
        "- **production_db_touched**: `False`",
        "- **real_config_upgrade_run**: `False`",
        f"- **baseline_table_count**: `{report['baseline_table_count']}`",
        f"- **create_table_count_before_patch**: `{report['create_table_count_before_patch']}`",
        f"- **collision_table_count**: `{report['collision_table_count']}`",
        f"- **change_count**: `{report['patch']['change_count']}`",
        "",
        "## Collision tables neutralized",
        "",
    ]

    if report["collision_tables"]:
        for table in report["collision_tables"]:
            lines.append(f"- `{table}`")
    else:
        lines.append("- none")

    lines.extend(["", "## Errors", ""])
    if report["errors"]:
        for err in report["errors"]:
            lines.append(f"- {err}")
    else:
        lines.append("- none")

    lines.extend(["", "## Changes", ""])
    if report["patch"]["changes"]:
        for c in report["patch"]["changes"][:250]:
            lines.append(f"### {c['kind']} `{c['table']}` line {c['line']}")
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
    else:
        lines.append("- no changes required")

    REPORT_MD.write_text("\n".join(lines))


if __name__ == "__main__":
    raise SystemExit(main())
