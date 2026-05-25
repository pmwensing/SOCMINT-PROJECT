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
VERSION = "12.10.48"

PROMOTED = ROOT / "migrations/versions/0018_approved_model_migration.py"
VALIDATION_JSON = ROOT / "release/approved_draft_validation/APPROVED_DRAFT_STATIC_VALIDATION_V12_10_36.json"

OUT_DIR = ROOT / "release/full_db_smoke_trace"
REPORT_JSON = OUT_DIR / "FULL_DB_SMOKE_TRACE_CAPTURE_V12_10_48.json"
REPORT_MD = OUT_DIR / "FULL_DB_SMOKE_TRACE_CAPTURE_V12_10_48.md"
FULL_STDOUT = OUT_DIR / "ALEMBIC_UPGRADE_HEAD_FULL_OUTPUT_V12_10_48.txt"
FULL_SQL = OUT_DIR / "ALEMBIC_UPGRADE_HEAD_SQL_MODE_V12_10_48.sql"
IDENTITY_BLOCKS = OUT_DIR / "IDENTITY_BLOCKS_FROM_0018_V12_10_48.md"
PATCH_DECISION = OUT_DIR / "NEXT_PATCH_DECISION_V12_10_48.md"

TARGET_TABLES = ["all_tab_identity_cols", "identity_columns"]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def run(cmd: List[str], env: Dict[str, str]) -> Tuple[int, str]:
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return proc.returncode, proc.stdout


def sqlite_tables(db_path: Path) -> List[str]:
    if not db_path.exists():
        return []
    con = sqlite3.connect(str(db_path))
    try:
        rows = con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
        return [r[0] for r in rows]
    finally:
        con.close()


def alembic_version(db_path: Path) -> str | None:
    if not db_path.exists():
        return None
    con = sqlite3.connect(str(db_path))
    try:
        rows = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'").fetchall()
        if not rows:
            return None
        row = con.execute("SELECT version_num FROM alembic_version LIMIT 1").fetchone()
        return row[0] if row else None
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

    dst = tmp_dir / "alembic_v12_10_48.ini"
    with dst.open("w") as f:
        cfg.write(f)

    return dst


def make_env(db_url: str) -> Dict[str, str]:
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

    env["V12_10_48_FULL_TRACE"] = "1"
    env["SOCMINT_LOG_FILE"] = str((OUT_DIR / "full_trace_socmint.log").resolve())
    return env


def extract_create_tables(text: str) -> List[str]:
    return re.findall(r'op\.create_table\(\s*(?:\n\s*)?["\']([^"\']+)["\']', text, re.MULTILINE)


def find_create_table_block(text: str, table: str) -> Tuple[int, int, str]:
    lines = text.splitlines()
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
        return -1, -1, ""

    depth = 0
    seen = False
    end = start

    for idx in range(start, len(lines)):
        depth += lines[idx].count("(")
        depth -= lines[idx].count(")")
        if "(" in lines[idx]:
            seen = True
        end = idx
        if seen and depth <= 0:
            break

    block = "\n".join(f"{i+1:04d}: {lines[i]}" for i in range(start, end + 1))
    return start + 1, end + 1, block


def extract_exception_summary(output: str) -> Dict[str, Any]:
    lines = output.splitlines()
    exception_lines = []

    patterns = [
        "Traceback",
        "sqlalchemy.exc.",
        "sqlite3.",
        "OperationalError",
        "CompileError",
        "ArgumentError",
        "IntegrityError",
        "TypeError",
        "ValueError",
        "NameError",
        "SyntaxError",
        "InvalidRequestError",
        "FAILED",
        "Error",
        "error",
    ]

    for line in lines:
        if any(p in line for p in patterns):
            exception_lines.append(line.rstrip())

    last_trace_idx = output.rfind("Traceback (most recent call last):")
    traceback = output[last_trace_idx:] if last_trace_idx >= 0 else output[-8000:]

    exact_exception = None
    for line in reversed(lines):
        if "sqlalchemy.exc." in line or "sqlite3." in line or re.search(r"(Error|Exception):", line):
            exact_exception = line.strip()
            break

    return {
        "exact_exception": exact_exception,
        "exception_lines": exception_lines[-200:],
        "traceback_tail": traceback[-12000:],
    }


def classify(output: str, sql_output: str) -> List[Dict[str, str]]:
    low = (output + "\n" + sql_output).lower()
    findings: List[Dict[str, str]] = []

    def add(kind: str, severity: str, repair: str) -> None:
        findings.append({"kind": kind, "severity": severity, "repair": repair})

    if "duplicate column name" in low:
        add("duplicate_column_name", "blocker", "Comment or rename the duplicate active column in the failing table block.")

    if "already exists" in low:
        add("already_exists", "blocker", "The migration creates an object already present from earlier migration; guard or remove duplicate create.")

    if "near" in low and "syntax error" in low:
        add("sqlite_syntax_error", "blocker", "Patch the exact DDL fragment near the syntax error. Check FULL SQL output.")

    if "multiple primary keys" in low or "more than one primary key" in low:
        add("multiple_primary_keys", "blocker", "Keep only one primary key or remove PKs from metadata tables for smoke.")

    if "unknown database" in low:
        add("qualified_table_name_or_schema", "blocker", "Remove schema-qualified table/constraint references for SQLite smoke.")

    if "foreign key mismatch" in low or "no such table" in low or "foreign key" in low:
        add("foreign_key_reference_issue", "blocker", "Remove/defer FK references for temp SQLite smoke.")

    if "default value" in low or "server_default" in low:
        add("invalid_default_expression", "blocker", "Remove server_default/default expression from failing metadata table.")

    if "autoincrement" in low or "identity" in low and "syntax" in low:
        add("identity_autoincrement_sqlite_incompatibility", "blocker", "Replace identity/autoincrement dialect feature with plain nullable metadata column for SQLite smoke.")

    if "not implemented" in low:
        add("sqlite_not_implemented", "blocker", "Remove unsupported SQLite DDL feature from temp smoke migration.")

    if not findings:
        add("unclassified_full_trace_failure", "review", "Open full trace and SQL output; classifier did not match known patterns.")

    # dedupe
    out = []
    seen = set()
    for f in findings:
        key = f["kind"]
        if key not in seen:
            seen.add(key)
            out.append(f)
    return out


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    validation = load_json(VALIDATION_JSON)
    approved_tables = validation.get("approved_tables", [])

    tmp_root = Path(tempfile.mkdtemp(prefix="socmint_v12_10_48_"))
    db_path = tmp_root / "dry_run_full_trace.sqlite"
    db_url = f"sqlite:///{db_path}"
    cfg = make_temp_alembic_config(tmp_root, db_url)
    env = make_env(db_url)

    heads_code, heads_out = run(["alembic", "-c", str(cfg), "heads"], env)
    sql_code, sql_out = run(["alembic", "-c", str(cfg), "upgrade", "head", "--sql"], env)
    FULL_SQL.write_text(sql_out)

    upgrade_code, upgrade_out = run(["alembic", "-c", str(cfg), "upgrade", "head"], env)
    FULL_STDOUT.write_text(upgrade_out)

    tables = sqlite_tables(db_path)
    version = alembic_version(db_path)

    created_approved = [t for t in approved_tables if t in set(tables)]
    missing_approved = [t for t in approved_tables if t not in set(tables)]

    migration_text = PROMOTED.read_text()
    identity_blocks = {}
    for table in TARGET_TABLES:
        start, end, block = find_create_table_block(migration_text, table)
        identity_blocks[table] = {"start_line": start, "end_line": end, "block": block, "found": bool(block)}

    exception = extract_exception_summary(upgrade_out)
    findings = classify(upgrade_out, sql_out)

    report = {
        "version": VERSION,
        "generated_at": now(),
        "schema_mutation": "temp_sqlite_only",
        "production_db_touched": False,
        "real_config_upgrade_run": False,
        "temp_root": str(tmp_root),
        "temp_db_path": str(db_path),
        "temp_alembic_config": str(cfg),
        "heads_returncode": heads_code,
        "upgrade_sql_returncode": sql_code,
        "upgrade_returncode": upgrade_code,
        "alembic_version_after_upgrade": version,
        "approved_table_count": len(approved_tables),
        "created_approved_table_count": len(created_approved),
        "missing_approved_table_count": len(missing_approved),
        "created_approved_tables": created_approved,
        "missing_approved_tables": missing_approved,
        "all_sqlite_tables": tables,
        "exception": exception,
        "findings": findings,
        "identity_blocks": identity_blocks,
        "full_upgrade_output": str(FULL_STDOUT),
        "full_sql_output": str(FULL_SQL),
        "next_action": "Build v12.10.49 exact migration patch from FULL_DB_SMOKE_TRACE_CAPTURE_V12_10_48.json",
    }

    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True))
    write_report(report)
    write_identity_blocks(report)
    write_patch_decision(report)

    print(json.dumps({
        "version": VERSION,
        "upgrade_returncode": upgrade_code,
        "alembic_version_after_upgrade": version,
        "created_approved_table_count": len(created_approved),
        "missing_approved_table_count": len(missing_approved),
        "missing_approved_tables": missing_approved,
        "exact_exception": exception.get("exact_exception"),
        "finding_count": len(findings),
        "schema_mutation": "temp_sqlite_only",
        "production_db_touched": False,
        "real_config_upgrade_run": False,
        "report_json": str(REPORT_JSON),
        "report_md": str(REPORT_MD),
        "full_upgrade_output": str(FULL_STDOUT),
        "full_sql_output": str(FULL_SQL),
        "patch_decision": str(PATCH_DECISION),
    }, indent=2, sort_keys=True))

    return 0


def write_report(report: Dict[str, Any]) -> None:
    lines = [
        "# v12.10.48 Full DB Smoke Trace Capture",
        "",
        f"- **upgrade_returncode**: `{report['upgrade_returncode']}`",
        f"- **alembic_version_after_upgrade**: `{report['alembic_version_after_upgrade']}`",
        "- **schema_mutation**: `temp_sqlite_only`",
        "- **production_db_touched**: `False`",
        "- **real_config_upgrade_run**: `False`",
        f"- **created_approved_table_count**: `{report['created_approved_table_count']}`",
        f"- **missing_approved_table_count**: `{report['missing_approved_table_count']}`",
        f"- **full_upgrade_output**: `{report['full_upgrade_output']}`",
        f"- **full_sql_output**: `{report['full_sql_output']}`",
        "",
        "## Exact exception",
        "",
        f"`{report['exception'].get('exact_exception')}`",
        "",
        "## Findings",
        "",
    ]

    for f in report["findings"]:
        lines.append(f"- **{f['kind']}** / `{f['severity']}` — {f['repair']}")

    lines.extend(["", "## Missing approved tables", ""])
    for table in report["missing_approved_tables"]:
        lines.append(f"- `{table}`")

    lines.extend(["", "## Exception lines", ""])
    for line in report["exception"].get("exception_lines", []):
        lines.append(f"- `{line}`")

    REPORT_MD.write_text("\n".join(lines))


def write_identity_blocks(report: Dict[str, Any]) -> None:
    lines = ["# v12.10.48 Identity Blocks", ""]
    for table, info in report["identity_blocks"].items():
        lines.extend([
            f"## `{table}`",
            "",
            f"- found: `{info['found']}`",
            f"- start_line: `{info['start_line']}`",
            f"- end_line: `{info['end_line']}`",
            "",
            "```python",
            info["block"],
            "```",
            "",
        ])
    IDENTITY_BLOCKS.write_text("\n".join(lines))


def write_patch_decision(report: Dict[str, Any]) -> None:
    lines = [
        "# v12.10.48 Next Patch Decision",
        "",
        "Use this for v12.10.49. Do not patch blindly.",
        "",
        "## Exact exception",
        "",
        f"`{report['exception'].get('exact_exception')}`",
        "",
        "## Findings",
        "",
    ]

    for f in report["findings"]:
        lines.extend([
            f"### {f['kind']}",
            "",
            f"- severity: `{f['severity']}`",
            f"- repair: {f['repair']}",
            "",
        ])

    lines.extend([
        "## Files to inspect",
        "",
        f"- `{report['full_upgrade_output']}`",
        f"- `{report['full_sql_output']}`",
        "- `release/full_db_smoke_trace/IDENTITY_BLOCKS_FROM_0018_V12_10_48.md`",
        "",
        "## Safety constraints",
        "",
        "- Patch only promoted 0018 unless generator cause is proven.",
        "- Keep TODOs as comments only.",
        "- Do not run real DB upgrade.",
        "- Rerun v12.10.38 and v12.10.39 after patch.",
    ])

    PATCH_DECISION.write_text("\n".join(lines))


if __name__ == "__main__":
    raise SystemExit(main())
