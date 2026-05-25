#!/usr/bin/env python3
from __future__ import annotations

import configparser
import json
import os
import shutil
import sqlite3
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


ROOT = Path.cwd()
VERSION = "12.10.38"

PROMOTION_MANIFEST = ROOT / "release/migration_promotion/MIGRATION_PROMOTION_MANIFEST_V12_10_37.json"
VALIDATION_REPORT = ROOT / "release/approved_draft_validation/APPROVED_DRAFT_STATIC_VALIDATION_V12_10_36.json"

OUT_DIR = ROOT / "release/db_migration_smoke"
REPORT_JSON = OUT_DIR / "DB_MIGRATION_SMOKE_V12_10_38.json"
REPORT_MD = OUT_DIR / "DB_MIGRATION_SMOKE_V12_10_38.md"
TEMP_INFO = OUT_DIR / "DB_MIGRATION_SMOKE_TEMP_DB_V12_10_38.txt"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(cmd: List[str], env: Dict[str, str]) -> Tuple[int, str]:
    try:
        out = subprocess.check_output(
            cmd,
            cwd=ROOT,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
        )
        return 0, out
    except subprocess.CalledProcessError as exc:
        return exc.returncode, exc.output


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"Missing required file: {path}")
    return json.loads(path.read_text())


def sqlite_tables(db_path: Path) -> List[str]:
    if not db_path.exists():
        return []

    con = sqlite3.connect(str(db_path))
    try:
        rows = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        return [r[0] for r in rows]
    finally:
        con.close()


def alembic_version(db_path: Path) -> str | None:
    if not db_path.exists():
        return None

    con = sqlite3.connect(str(db_path))
    try:
        tables = sqlite_tables(db_path)
        if "alembic_version" not in tables:
            return None
        row = con.execute("SELECT version_num FROM alembic_version LIMIT 1").fetchone()
        return row[0] if row else None
    finally:
        con.close()


def make_temp_alembic_config(tmp_dir: Path, db_url: str) -> Path:
    src = ROOT / "alembic.ini"
    if not src.exists():
        raise SystemExit("Missing alembic.ini")

    dst = tmp_dir / "alembic_v12_10_38.ini"
    cfg = configparser.ConfigParser()
    cfg.read(src)

    if not cfg.has_section("alembic"):
        cfg.add_section("alembic")

    script_location = cfg.get("alembic", "script_location", fallback="migrations")
    cfg.set("alembic", "script_location", str((ROOT / script_location).resolve()))
    cfg.set("alembic", "sqlalchemy.url", db_url)

    with dst.open("w") as f:
        cfg.write(f)

    return dst


def temp_env(db_url: str) -> Dict[str, str]:
    env = os.environ.copy()

    # Common names used by Flask/FastAPI/SQLAlchemy/Alembic env.py files.
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

    env["V12_10_38_DRY_RUN_DB_SMOKE"] = "1"
    env["SOCMINT_LOG_FILE"] = str((OUT_DIR / "dry_run_socmint.log").resolve())

    return env


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    promotion = load_json(PROMOTION_MANIFEST)
    validation = load_json(VALIDATION_REPORT)

    approved_tables = promotion.get("approved_tables") or validation.get("approved_tables") or []
    approved_tables = list(dict.fromkeys(approved_tables))

    errors: List[str] = []
    warnings: List[str] = []
    steps: List[Dict[str, Any]] = []

    if promotion.get("promotion_status") != "PROMOTED":
        errors.append(f"v12.10.37 promotion_status is not PROMOTED: {promotion.get('promotion_status')}")

    if validation.get("promotion_status") != "GO":
        errors.append(f"v12.10.36 promotion_status is not GO: {validation.get('promotion_status')}")

    if not approved_tables:
        errors.append("No approved tables found in manifests")

    tmp_root = Path(tempfile.mkdtemp(prefix="socmint_v12_10_38_"))
    db_path = tmp_root / "dry_run.sqlite"
    db_url = f"sqlite:///{db_path}"

    cfg_path = make_temp_alembic_config(tmp_root, db_url)
    env = temp_env(db_url)

    TEMP_INFO.write_text(
        "\n".join([
            f"tmp_root={tmp_root}",
            f"db_path={db_path}",
            f"db_url={db_url}",
            f"alembic_config={cfg_path}",
            "production_db_touched=false",
        ]) + "\n"
    )

    if not errors:
        code, out = run(["alembic", "-c", str(cfg_path), "heads"], env)
        steps.append({"step": "alembic_heads_temp_config", "returncode": code, "output": out[-4000:]})
        if code != 0:
            errors.append("alembic heads failed under temp config")

    if not errors:
        code, out = run(["alembic", "-c", str(cfg_path), "upgrade", "head"], env)
        steps.append({"step": "upgrade_head_temp_sqlite", "returncode": code, "output": out[-8000:]})
        if code != 0:
            errors.append("alembic upgrade head failed against temp SQLite DB")

    tables_after_upgrade = sqlite_tables(db_path)
    version_after_upgrade = alembic_version(db_path)

    missing_after_upgrade = sorted(set(approved_tables) - set(tables_after_upgrade))
    if not errors and missing_after_upgrade:
        errors.append("approved 0018 tables missing after upgrade: " + ", ".join(missing_after_upgrade))

    if not errors and version_after_upgrade != "0018_approved_model_migration":
        errors.append(f"alembic_version after upgrade is {version_after_upgrade}, expected 0018_approved_model_migration")

    if not errors:
        code, out = run(["alembic", "-c", str(cfg_path), "downgrade", "0017_v12_10_schema_reconciliation"], env)
        steps.append({"step": "downgrade_to_0017_temp_sqlite", "returncode": code, "output": out[-8000:]})
        if code != 0:
            errors.append("alembic downgrade to 0017 failed against temp SQLite DB")

    tables_after_downgrade = sqlite_tables(db_path)
    version_after_downgrade = alembic_version(db_path)

    lingering_after_downgrade = sorted(set(approved_tables) & set(tables_after_downgrade))
    if not errors and lingering_after_downgrade:
        errors.append("approved 0018 tables still exist after downgrade to 0017: " + ", ".join(lingering_after_downgrade))

    if not errors and version_after_downgrade != "0017_v12_10_schema_reconciliation":
        errors.append(f"alembic_version after downgrade is {version_after_downgrade}, expected 0017_v12_10_schema_reconciliation")

    smoke_status = "GO" if not errors else "NO-GO"

    report = {
        "version": VERSION,
        "generated_at": utc_now(),
        "smoke_status": smoke_status,
        "schema_mutation": "temp_sqlite_only",
        "production_db_touched": False,
        "real_config_upgrade_run": False,
        "alembic_upgrade_head_run_on_temp_db": any(s["step"] == "upgrade_head_temp_sqlite" for s in steps),
        "alembic_downgrade_run_on_temp_db": any(s["step"] == "downgrade_to_0017_temp_sqlite" for s in steps),
        "temp_root": str(tmp_root),
        "temp_db_path": str(db_path),
        "temp_alembic_config": str(cfg_path),
        "approved_table_count": len(approved_tables),
        "approved_tables": approved_tables,
        "tables_after_upgrade_count": len(tables_after_upgrade),
        "tables_after_upgrade": tables_after_upgrade,
        "missing_after_upgrade": missing_after_upgrade,
        "version_after_upgrade": version_after_upgrade,
        "tables_after_downgrade_count": len(tables_after_downgrade),
        "tables_after_downgrade": tables_after_downgrade,
        "lingering_after_downgrade": lingering_after_downgrade,
        "version_after_downgrade": version_after_downgrade,
        "errors": errors,
        "warnings": warnings,
        "steps": steps,
    }

    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True))
    write_md(report)

    print(json.dumps({
        "version": VERSION,
        "smoke_status": smoke_status,
        "production_db_touched": False,
        "real_config_upgrade_run": False,
        "approved_table_count": len(approved_tables),
        "tables_after_upgrade_count": len(tables_after_upgrade),
        "missing_after_upgrade_count": len(missing_after_upgrade),
        "lingering_after_downgrade_count": len(lingering_after_downgrade),
        "version_after_upgrade": version_after_upgrade,
        "version_after_downgrade": version_after_downgrade,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "report_json": str(REPORT_JSON),
        "report_md": str(REPORT_MD),
        "temp_db_path": str(db_path),
    }, indent=2, sort_keys=True))

    return 0 if smoke_status == "GO" else 1


def write_md(report: Dict[str, Any]) -> None:
    lines = [
        "# v12.10.38 Dry-Run DB Migration Smoke Report",
        "",
        f"- **smoke_status**: `{report['smoke_status']}`",
        "- **schema_mutation**: `temp_sqlite_only`",
        "- **production_db_touched**: `False`",
        "- **real_config_upgrade_run**: `False`",
        f"- **approved_table_count**: `{report['approved_table_count']}`",
        f"- **tables_after_upgrade_count**: `{report['tables_after_upgrade_count']}`",
        f"- **missing_after_upgrade**: `{len(report['missing_after_upgrade'])}`",
        f"- **lingering_after_downgrade**: `{len(report['lingering_after_downgrade'])}`",
        f"- **version_after_upgrade**: `{report['version_after_upgrade']}`",
        f"- **version_after_downgrade**: `{report['version_after_downgrade']}`",
        f"- **temp_db_path**: `{report['temp_db_path']}`",
        "",
        "## Errors",
        "",
    ]

    if report["errors"]:
        for err in report["errors"]:
            lines.append(f"- {err}")
    else:
        lines.append("- none")

    lines.extend(["", "## Warnings", ""])

    if report["warnings"]:
        for warning in report["warnings"]:
            lines.append(f"- {warning}")
    else:
        lines.append("- none")

    lines.extend(["", "## Step outputs", ""])

    for step in report["steps"]:
        lines.append(f"### {step['step']} returncode={step['returncode']}")
        lines.append("")
        lines.append("```text")
        lines.append(step["output"])
        lines.append("```")
        lines.append("")

    REPORT_MD.write_text("\n".join(lines))


if __name__ == "__main__":
    raise SystemExit(main())
