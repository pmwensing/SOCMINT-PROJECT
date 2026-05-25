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
VERSION = "12.10.50"
BASE_REV = "0017_v12_10_schema_reconciliation"

VALIDATION_JSON = ROOT / "release/approved_draft_validation/APPROVED_DRAFT_STATIC_VALIDATION_V12_10_36.json"
SMOKE_JSON = ROOT / "release/db_migration_smoke/DB_MIGRATION_SMOKE_V12_10_38.json"

OUT_DIR = ROOT / "release/downgrade_symmetry_repair"
REPORT_JSON = OUT_DIR / "DOWNGRADE_SYMMETRY_REPAIR_V12_10_50.json"
REPORT_MD = OUT_DIR / "DOWNGRADE_SYMMETRY_REPAIR_V12_10_50.md"


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


def load_json(path: Path) -> Dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def active_versions_dir() -> Path:
    cfg = configparser.ConfigParser()
    cfg.read(ROOT / "alembic.ini")
    script_location = cfg.get("alembic", "script_location", fallback="migrations")
    return ROOT / script_location / "versions"


def migration_path() -> Path:
    return active_versions_dir() / "0018_approved_model_migration.py"


def make_temp_config(tmp_root: Path, db_url: str) -> Path:
    cfg = configparser.ConfigParser()
    cfg.read(ROOT / "alembic.ini")

    if not cfg.has_section("alembic"):
        cfg.add_section("alembic")

    script_location = cfg.get("alembic", "script_location", fallback="migrations")
    cfg.set("alembic", "script_location", str((ROOT / script_location).resolve()))
    cfg.set("alembic", "sqlalchemy.url", db_url)

    out = tmp_root / "alembic_v12_10_50.ini"
    with out.open("w") as f:
        cfg.write(f)
    return out


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
    env["V12_10_50_DOWNGRADE_REPAIR"] = "1"
    env["SOCMINT_LOG_FILE"] = str((OUT_DIR / "downgrade_repair_socmint.log").resolve())
    return env


def sqlite_tables(db_path: Path) -> List[str]:
    if not db_path.exists():
        return []
    con = sqlite3.connect(str(db_path))
    try:
        rows = con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
        return [r[0] for r in rows]
    finally:
        con.close()


def baseline_0017_tables() -> Dict[str, object]:
    tmp_root = Path(tempfile.mkdtemp(prefix="socmint_v12_10_50_base_"))
    db_path = tmp_root / "baseline.sqlite"
    db_url = f"sqlite:///{db_path}"
    cfg = make_temp_config(tmp_root, db_url)
    env = temp_env(db_url)

    code, out = run(["alembic", "-c", str(cfg), "upgrade", BASE_REV], env)
    return {
        "tmp_root": str(tmp_root),
        "db_path": str(db_path),
        "returncode": code,
        "output": out,
        "tables": sqlite_tables(db_path),
    }


def extract_create_tables(text: str) -> List[str]:
    return re.findall(r'op\.create_table\(\s*(?:\n\s*)?["\']([^"\']+)["\']', text, re.MULTILINE)


def extract_active_drop_tables(text: str) -> List[str]:
    tables = []
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            continue
        m = re.search(r'op\.drop_table\(\s*["\']([^"\']+)["\']', line)
        if m:
            tables.append(m.group(1))
    return tables


def find_downgrade_function(lines: List[str]) -> Tuple[int, int]:
    start = -1
    for idx, line in enumerate(lines):
        if re.match(r"^def\s+downgrade\s*\(", line):
            start = idx
            break

    if start < 0:
        return -1, -1

    end = len(lines) - 1
    for idx in range(start + 1, len(lines)):
        if re.match(r"^def\s+\w+\s*\(", lines[idx]):
            end = idx - 1
            break

    return start, end


def repair_downgrade(text: str, approved_tables: List[str], baseline_tables: List[str]) -> Tuple[str, List[Dict[str, object]]]:
    lines = text.splitlines()
    start, end = find_downgrade_function(lines)
    if start < 0:
        raise SystemExit("Could not find downgrade() in promoted migration")

    baseline_set = set(baseline_tables)
    approved_owned = [t for t in approved_tables if t not in baseline_set]
    desired_drop_order = list(reversed(approved_owned))

    active_drop_tables = extract_active_drop_tables(text)
    active_set = set(active_drop_tables)

    missing_drops = [t for t in desired_drop_order if t not in active_set]

    changes: List[Dict[str, object]] = []

    # Insert missing drop calls immediately after downgrade() comments/header.
    insert_at = start + 1
    while insert_at <= end and (
        not lines[insert_at].strip()
        or lines[insert_at].lstrip().startswith("#")
    ):
        insert_at += 1

    new_lines = lines[:]
    insert_lines = []

    for table in missing_drops:
        line = f'    op.drop_table("{table}")  # v12.10.50 restored downgrade symmetry for 0018-owned table'
        insert_lines.append(line)
        changes.append({
            "kind": "insert_missing_drop",
            "table": table,
            "line": insert_at + len(insert_lines),
            "after": line,
        })

    if insert_lines:
        new_lines = new_lines[:insert_at] + insert_lines + new_lines[insert_at:]

    # Ensure baseline tables are not actively dropped.
    baseline_drop_pattern_tables = []
    final_lines = []
    for idx, line in enumerate(new_lines, 1):
        m = re.search(r'op\.drop_table\(\s*["\']([^"\']+)["\']', line)
        if m and not line.lstrip().startswith("#"):
            table = m.group(1)
            if table in baseline_set:
                indent = line[:len(line) - len(line.lstrip())]
                patched = indent + "# " + line.lstrip() + "  # TODO: baseline table existed at 0017; do not drop in 0018 downgrade"
                final_lines.append(patched)
                baseline_drop_pattern_tables.append(table)
                changes.append({
                    "kind": "comment_baseline_drop",
                    "table": table,
                    "line": idx,
                    "before": line,
                    "after": patched,
                })
                continue
        final_lines.append(line)

    return "\n".join(final_lines) + "\n", changes


def validate_migration() -> Dict[str, object]:
    p = migration_path()
    py_code, py_out = run(["python", "-m", "py_compile", str(p)])
    heads_code, heads_out = run(["alembic", "heads"])

    return {
        "py_compile": {"returncode": py_code, "output": py_out},
        "alembic_heads": {"returncode": heads_code, "output": heads_out},
        "ok": py_code == 0 and heads_code == 0 and "0018_approved_model_migration" in heads_out,
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    validation = load_json(VALIDATION_JSON)
    smoke = load_json(SMOKE_JSON)

    approved_tables = list(validation.get("approved_tables", []))
    if not approved_tables:
        approved_tables = list(smoke.get("approved_tables", []))

    if not approved_tables:
        raise SystemExit("No approved tables available for downgrade symmetry repair")

    baseline = baseline_0017_tables()
    if baseline["returncode"] != 0:
        raise SystemExit("Could not build 0017 temp baseline:\n" + str(baseline["output"]))

    p = migration_path()
    if not p.exists():
        raise SystemExit(f"Missing promoted migration: {p}")

    before = p.read_text()
    before_active_drops = extract_active_drop_tables(before)

    repaired, changes = repair_downgrade(before, approved_tables, list(baseline["tables"]))
    p.write_text(repaired)

    after = p.read_text()
    after_active_drops = extract_active_drop_tables(after)

    owned_tables = [t for t in approved_tables if t not in set(baseline["tables"])]
    missing_after_repair = [t for t in owned_tables if t not in set(after_active_drops)]

    migration_validation = validate_migration()

    errors = []
    if not migration_validation["ok"]:
        errors.append("promoted migration failed compile/head validation")
    if missing_after_repair:
        errors.append("owned approved tables still missing active drop_table: " + ", ".join(missing_after_repair))

    report = {
        "version": VERSION,
        "generated_at": now(),
        "schema_mutation": "none",
        "production_db_touched": False,
        "real_config_upgrade_run": False,
        "promoted_migration": str(p),
        "approved_table_count": len(approved_tables),
        "baseline_table_count": len(baseline["tables"]),
        "owned_0018_table_count": len(owned_tables),
        "owned_0018_tables": owned_tables,
        "before_active_drop_count": len(before_active_drops),
        "before_active_drops": before_active_drops,
        "after_active_drop_count": len(after_active_drops),
        "after_active_drops": after_active_drops,
        "missing_after_repair": missing_after_repair,
        "change_count": len(changes),
        "changes": changes,
        "migration_validation": migration_validation,
        "errors": errors,
        "repair_status": "GO" if not errors else "NO-GO",
    }

    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True))
    write_md(report)

    print(json.dumps({
        "version": VERSION,
        "repair_status": report["repair_status"],
        "approved_table_count": len(approved_tables),
        "owned_0018_table_count": len(owned_tables),
        "before_active_drop_count": len(before_active_drops),
        "after_active_drop_count": len(after_active_drops),
        "missing_after_repair_count": len(missing_after_repair),
        "change_count": len(changes),
        "schema_mutation": "none",
        "production_db_touched": False,
        "real_config_upgrade_run": False,
        "report_json": str(REPORT_JSON),
        "report_md": str(REPORT_MD),
    }, indent=2, sort_keys=True))

    return 0 if not errors else 1


def write_md(report: Dict[str, object]) -> None:
    lines = [
        "# v12.10.50 Downgrade Symmetry Repair",
        "",
        f"- **repair_status**: `{report['repair_status']}`",
        "- **schema_mutation**: `none`",
        "- **production_db_touched**: `False`",
        "- **real_config_upgrade_run**: `False`",
        f"- **approved_table_count**: `{report['approved_table_count']}`",
        f"- **owned_0018_table_count**: `{report['owned_0018_table_count']}`",
        f"- **before_active_drop_count**: `{report['before_active_drop_count']}`",
        f"- **after_active_drop_count**: `{report['after_active_drop_count']}`",
        f"- **missing_after_repair**: `{len(report['missing_after_repair'])}`",
        f"- **change_count**: `{report['change_count']}`",
        "",
        "## Errors",
        "",
    ]

    if report["errors"]:
        for err in report["errors"]:
            lines.append(f"- {err}")
    else:
        lines.append("- none")

    lines.extend(["", "## 0018-owned tables", ""])
    for table in report["owned_0018_tables"]:
        lines.append(f"- `{table}`")

    lines.extend(["", "## Changes", ""])
    if report["changes"]:
        for c in report["changes"]:
            lines.append(f"- **{c['kind']}** `{c['table']}` line `{c['line']}`")
    else:
        lines.append("- no changes required")

    REPORT_MD.write_text("\n".join(lines))


if __name__ == "__main__":
    raise SystemExit(main())
