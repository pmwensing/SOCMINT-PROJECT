#!/usr/bin/env python3
from __future__ import annotations

import configparser
import json
import os
import sqlite3
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


ROOT = Path.cwd()
VERSION = "12.10.51"

BASE_REV = "0017_v12_10_schema_reconciliation"
HEAD_REV = "0018_approved_model_migration"

VALIDATION_JSON = ROOT / "release/approved_draft_validation/APPROVED_DRAFT_STATIC_VALIDATION_V12_10_36.json"

OUT_DIR = ROOT / "release/baseline_aware_db_smoke"
REPORT_JSON = OUT_DIR / "BASELINE_AWARE_DB_SMOKE_GATE_V12_10_51.json"
REPORT_MD = OUT_DIR / "BASELINE_AWARE_DB_SMOKE_GATE_V12_10_51.md"
PROMOTION_READY = OUT_DIR / "BASELINE_AWARE_PROMOTION_READY_V12_10_51.json"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


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


def make_temp_config(tmp_root: Path, db_url: str) -> Path:
    cfg = configparser.ConfigParser()
    cfg.read(ROOT / "alembic.ini")

    if not cfg.has_section("alembic"):
        cfg.add_section("alembic")

    script_location = cfg.get("alembic", "script_location", fallback="migrations")
    cfg.set("alembic", "script_location", str((ROOT / script_location).resolve()))
    cfg.set("alembic", "sqlalchemy.url", db_url)

    out = tmp_root / "alembic_v12_10_51.ini"
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

    env["V12_10_51_BASELINE_AWARE_SMOKE"] = "1"
    env["SOCMINT_LOG_FILE"] = str((OUT_DIR / "baseline_aware_socmint.log").resolve())

    return env


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    validation = load_json(VALIDATION_JSON)
    approved_tables = list(validation.get("approved_tables", []))

    if not approved_tables:
        raise SystemExit("No approved tables found in v12.10.36 validation JSON")

    tmp_root = Path(tempfile.mkdtemp(prefix="socmint_v12_10_51_"))
    db_path = tmp_root / "baseline_aware.sqlite"
    db_url = f"sqlite:///{db_path}"
    cfg = make_temp_config(tmp_root, db_url)
    env = temp_env(db_url)

    steps: List[Dict[str, Any]] = []
    errors: List[str] = []
    warnings: List[str] = []

    code, out = run(["alembic", "-c", str(cfg), "upgrade", BASE_REV], env)
    steps.append({"step": "upgrade_to_0017_baseline", "returncode": code, "output": out})
    if code != 0:
        errors.append("failed to upgrade temp DB to 0017 baseline")

    baseline_tables = sqlite_tables(db_path)
    version_after_baseline = alembic_version(db_path)

    approved_baseline_tables = sorted(set(approved_tables) & set(baseline_tables))
    owned_0018_tables = [t for t in approved_tables if t not in set(baseline_tables)]

    if not errors:
        code, out = run(["alembic", "-c", str(cfg), "upgrade", "head"], env)
        steps.append({"step": "upgrade_to_head_0018", "returncode": code, "output": out})
        if code != 0:
            errors.append("failed to upgrade temp DB from 0017 to head")

    tables_after_upgrade = sqlite_tables(db_path)
    version_after_upgrade = alembic_version(db_path)

    missing_after_upgrade = sorted(set(approved_tables) - set(tables_after_upgrade))
    if missing_after_upgrade:
        errors.append("approved tables missing after upgrade: " + ", ".join(missing_after_upgrade))

    if version_after_upgrade != HEAD_REV:
        errors.append(f"version_after_upgrade={version_after_upgrade}; expected {HEAD_REV}")

    if not errors:
        code, out = run(["alembic", "-c", str(cfg), "downgrade", BASE_REV], env)
        steps.append({"step": "downgrade_back_to_0017", "returncode": code, "output": out})
        if code != 0:
            errors.append("failed to downgrade temp DB back to 0017")

    tables_after_downgrade = sqlite_tables(db_path)
    version_after_downgrade = alembic_version(db_path)

    owned_lingering_after_downgrade = sorted(set(owned_0018_tables) & set(tables_after_downgrade))
    baseline_missing_after_downgrade = sorted(set(approved_baseline_tables) - set(tables_after_downgrade))

    if owned_lingering_after_downgrade:
        errors.append("true 0018-owned tables still linger after downgrade: " + ", ".join(owned_lingering_after_downgrade))

    if baseline_missing_after_downgrade:
        errors.append("baseline-approved tables were incorrectly dropped by downgrade: " + ", ".join(baseline_missing_after_downgrade))

    if version_after_downgrade != BASE_REV:
        errors.append(f"version_after_downgrade={version_after_downgrade}; expected {BASE_REV}")

    status = "GO" if not errors else "NO-GO"
    release_status = "PASS GO" if status == "GO" else "HOLD"

    report = {
        "version": VERSION,
        "generated_at": now(),
        "baseline_revision": BASE_REV,
        "head_revision": HEAD_REV,
        "status": status,
        "release_status": release_status,
        "schema_lock": "BASELINE_AWARE_DB_SMOKE_GO" if status == "GO" else "BASELINE_AWARE_DB_SMOKE_HOLD",
        "schema_mutation": "temp_sqlite_only",
        "production_db_touched": False,
        "real_config_upgrade_run": False,
        "temp_root": str(tmp_root),
        "temp_db_path": str(db_path),
        "temp_alembic_config": str(cfg),
        "approved_table_count": len(approved_tables),
        "approved_tables": approved_tables,
        "baseline_table_count": len(baseline_tables),
        "approved_baseline_table_count": len(approved_baseline_tables),
        "approved_baseline_tables": approved_baseline_tables,
        "owned_0018_table_count": len(owned_0018_tables),
        "owned_0018_tables": owned_0018_tables,
        "version_after_baseline": version_after_baseline,
        "version_after_upgrade": version_after_upgrade,
        "version_after_downgrade": version_after_downgrade,
        "tables_after_upgrade_count": len(tables_after_upgrade),
        "missing_after_upgrade": missing_after_upgrade,
        "tables_after_downgrade_count": len(tables_after_downgrade),
        "owned_lingering_after_downgrade": owned_lingering_after_downgrade,
        "baseline_missing_after_downgrade": baseline_missing_after_downgrade,
        "errors": errors,
        "warnings": warnings,
        "steps": [
            {
                "step": s["step"],
                "returncode": s["returncode"],
                "output_tail": s["output"][-5000:],
            }
            for s in steps
        ],
    }

    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True))
    write_md(report)

    if status == "GO":
        PROMOTION_READY.write_text(json.dumps({
            "version": VERSION,
            "generated_at": now(),
            "promotion_ready": True,
            "release_status": "PASS GO",
            "schema_lock": report["schema_lock"],
            "head_revision": HEAD_REV,
            "baseline_revision": BASE_REV,
            "approved_table_count": len(approved_tables),
            "owned_0018_table_count": len(owned_0018_tables),
            "approved_baseline_table_count": len(approved_baseline_tables),
            "production_db_touched": False,
            "real_config_upgrade_run": False,
            "source_report": str(REPORT_JSON),
            "next_build": "v12.10.52 final release readiness manifest",
        }, indent=2, sort_keys=True))

    print(json.dumps({
        "version": VERSION,
        "status": status,
        "release_status": release_status,
        "schema_lock": report["schema_lock"],
        "approved_table_count": len(approved_tables),
        "approved_baseline_table_count": len(approved_baseline_tables),
        "owned_0018_table_count": len(owned_0018_tables),
        "missing_after_upgrade_count": len(missing_after_upgrade),
        "owned_lingering_after_downgrade_count": len(owned_lingering_after_downgrade),
        "baseline_missing_after_downgrade_count": len(baseline_missing_after_downgrade),
        "version_after_upgrade": version_after_upgrade,
        "version_after_downgrade": version_after_downgrade,
        "production_db_touched": False,
        "real_config_upgrade_run": False,
        "report_json": str(REPORT_JSON),
        "report_md": str(REPORT_MD),
        "promotion_ready": str(PROMOTION_READY),
    }, indent=2, sort_keys=True))

    return 0 if status == "GO" else 1


def write_md(report: Dict[str, Any]) -> None:
    lines = [
        "# v12.10.51 Baseline-Aware DB Smoke Gate",
        "",
        f"- **status**: `{report['status']}`",
        f"- **release_status**: `{report['release_status']}`",
        f"- **schema_lock**: `{report['schema_lock']}`",
        "- **schema_mutation**: `temp_sqlite_only`",
        "- **production_db_touched**: `False`",
        "- **real_config_upgrade_run**: `False`",
        f"- **baseline_revision**: `{report['baseline_revision']}`",
        f"- **head_revision**: `{report['head_revision']}`",
        f"- **version_after_upgrade**: `{report['version_after_upgrade']}`",
        f"- **version_after_downgrade**: `{report['version_after_downgrade']}`",
        f"- **approved_table_count**: `{report['approved_table_count']}`",
        f"- **approved_baseline_table_count**: `{report['approved_baseline_table_count']}`",
        f"- **owned_0018_table_count**: `{report['owned_0018_table_count']}`",
        f"- **missing_after_upgrade**: `{len(report['missing_after_upgrade'])}`",
        f"- **owned_lingering_after_downgrade**: `{len(report['owned_lingering_after_downgrade'])}`",
        f"- **baseline_missing_after_downgrade**: `{len(report['baseline_missing_after_downgrade'])}`",
        "",
        "## True 0018-owned tables",
        "",
    ]

    for table in report["owned_0018_tables"]:
        lines.append(f"- `{table}`")

    lines.extend(["", "## Approved baseline tables allowed to remain after downgrade", ""])

    for table in report["approved_baseline_tables"]:
        lines.append(f"- `{table}`")

    lines.extend(["", "## Errors", ""])

    if report["errors"]:
        for err in report["errors"]:
            lines.append(f"- {err}")
    else:
        lines.append("- none")

    REPORT_MD.write_text("\n".join(lines))


if __name__ == "__main__":
    raise SystemExit(main())
