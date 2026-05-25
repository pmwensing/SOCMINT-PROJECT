from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


VERSION = "12.10.54"
EXPECTED_RELEASE_TAG = "v12.10.53"
EXPECTED_ALEMBIC_HEAD = "0018_approved_model_migration"
EXPECTED_SCHEMA_LOCK = "BASELINE_AWARE_DB_SMOKE_GO"

ROOT = Path.cwd()
RELEASE_53B = ROOT / "release/v12_10_53B/FINAL_TAG_MANIFEST_HEAD_SYNC_V12_10_53B.json"
TAG_READY_53A = ROOT / "release/v12_10_53A/TAG_READY_MANIFEST_V12_10_53A.json"
PACKAGE_53 = ROOT / "release/v12_10_53/RELEASE_ARTIFACT_MANIFEST_V12_10_53.json"

TARBALL = ROOT / "dist/SOCMINT-PROJECT-v12.10.53-release.tar.gz"
ZIPFILE = ROOT / "dist/SOCMINT-PROJECT-v12.10.53-release.zip"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(cmd: List[str]) -> Tuple[int, str]:
    try:
        out = subprocess.check_output(cmd, cwd=ROOT, stderr=subprocess.STDOUT, text=True)
        return 0, out.strip()
    except subprocess.CalledProcessError as exc:
        return exc.returncode, exc.output.strip()


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def sha256(path: Path) -> str | None:
    if not path.exists():
        return None

    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class RuntimeSchemaStatus:
    version: str
    generated_at: str
    release_tag: str
    expected_alembic_head: str
    live_alembic_head: str | None
    schema_lock: str | None
    release_status: str | None
    final_tag_ready: bool
    production_db_touched: bool
    real_config_upgrade_run: bool
    real_db_upgrade_default_blocked: bool
    compatible: bool
    errors: List[str]
    warnings: List[str]


def release_state() -> Dict[str, Any]:
    return {
        "final_tag_sync": load_json(RELEASE_53B),
        "tag_ready": load_json(TAG_READY_53A),
        "package": load_json(PACKAGE_53),
    }


def live_alembic_head() -> str | None:
    code, out = run(["alembic", "heads"])
    if code != 0:
        return None
    return out


def runtime_schema_status() -> Dict[str, Any]:
    state = release_state()
    final_tag = state["final_tag_sync"]
    tag_ready = state["tag_ready"]
    package = state["package"]

    head = live_alembic_head()

    errors: List[str] = []
    warnings: List[str] = []

    if EXPECTED_ALEMBIC_HEAD not in str(head):
        errors.append(f"live Alembic head does not include {EXPECTED_ALEMBIC_HEAD}: {head}")

    schema_lock = final_tag.get("schema_lock") or tag_ready.get("schema_lock") or package.get("schema_lock")
    if schema_lock != EXPECTED_SCHEMA_LOCK:
        errors.append(f"schema_lock mismatch: {schema_lock}")

    release_status = final_tag.get("release_status") or tag_ready.get("release_status") or package.get("release_status")
    if release_status != "PASS GO":
        errors.append(f"release_status mismatch: {release_status}")

    final_tag_ready = bool(final_tag.get("final_tag_ready") or tag_ready.get("tag_ready"))
    if not final_tag_ready:
        errors.append("final tag-ready state is not true")

    production_db_touched = bool(
        final_tag.get("production_db_touched")
        or tag_ready.get("production_db_touched")
        or package.get("production_db_touched")
    )
    if production_db_touched:
        errors.append("release state indicates production DB was touched")

    real_config_upgrade_run = bool(
        final_tag.get("real_config_upgrade_run")
        or tag_ready.get("real_config_upgrade_run")
        or package.get("real_config_upgrade_run")
    )
    if real_config_upgrade_run:
        errors.append("release state indicates real configured DB upgrade was run")

    if os.environ.get("SOCMINT_ALLOW_REAL_DB_UPGRADE") == "YES_I_UNDERSTAND_REAL_DB_MIGRATION":
        warnings.append("operator override environment variable is present; real DB upgrade guard can be opened by migration gate")
    else:
        warnings.append("real DB upgrade is blocked by default")

    status = RuntimeSchemaStatus(
        version=VERSION,
        generated_at=utc_now(),
        release_tag=EXPECTED_RELEASE_TAG,
        expected_alembic_head=EXPECTED_ALEMBIC_HEAD,
        live_alembic_head=head,
        schema_lock=schema_lock,
        release_status=release_status,
        final_tag_ready=final_tag_ready,
        production_db_touched=production_db_touched,
        real_config_upgrade_run=real_config_upgrade_run,
        real_db_upgrade_default_blocked=True,
        compatible=not errors,
        errors=errors,
        warnings=warnings,
    )

    return asdict(status)


def assert_real_db_upgrade_allowed() -> Dict[str, Any]:
    """Fail closed unless the operator explicitly confirms real DB migration.

    This function intentionally does not run Alembic. It only validates whether a
    future command is allowed to proceed.
    """
    required = "YES_I_UNDERSTAND_REAL_DB_MIGRATION"
    value = os.environ.get("SOCMINT_ALLOW_REAL_DB_UPGRADE", "")

    allowed = value == required

    return {
        "version": VERSION,
        "allowed": allowed,
        "required_env": "SOCMINT_ALLOW_REAL_DB_UPGRADE",
        "required_value": required,
        "actual_value_present": bool(value),
        "production_db_touched": False,
        "real_config_upgrade_run": False,
        "message": "real DB upgrade explicitly allowed by operator" if allowed else "real DB upgrade blocked by default",
    }


def archive_integrity() -> Dict[str, Any]:
    package = load_json(PACKAGE_53)

    expected_tar = package.get("archives", {}).get("tarball", {}).get("sha256")
    expected_zip = package.get("archives", {}).get("zip", {}).get("sha256")

    actual_tar = sha256(TARBALL)
    actual_zip = sha256(ZIPFILE)

    errors = []
    if actual_tar != expected_tar:
        errors.append("tarball sha256 mismatch")
    if actual_zip != expected_zip:
        errors.append("zip sha256 mismatch")

    return {
        "version": VERSION,
        "generated_at": utc_now(),
        "tarball": str(TARBALL),
        "tarball_sha256": actual_tar,
        "tarball_expected_sha256": expected_tar,
        "zip": str(ZIPFILE),
        "zip_sha256": actual_zip,
        "zip_expected_sha256": expected_zip,
        "integrity_ok": not errors,
        "errors": errors,
        "production_db_touched": False,
        "real_config_upgrade_run": False,
    }


def version_payload() -> Dict[str, Any]:
    code, commit = run(["git", "rev-parse", "--short", "HEAD"])
    branch_code, branch = run(["git", "branch", "--show-current"])

    return {
        "version": VERSION,
        "release_tag": EXPECTED_RELEASE_TAG,
        "branch": branch if branch_code == 0 else None,
        "commit": commit if code == 0 else None,
        "alembic_head": live_alembic_head(),
        "schema_lock": EXPECTED_SCHEMA_LOCK,
        "production_db_touched": False,
        "real_config_upgrade_run": False,
    }


def rollback_instructions() -> Dict[str, Any]:
    return {
        "version": VERSION,
        "target_revision": EXPECTED_ALEMBIC_HEAD,
        "rollback_to": "0017_v12_10_schema_reconciliation",
        "safe_default": "Do not run automatically.",
        "operator_steps": [
            "Back up the real database first.",
            "Verify the deployed code and DB target.",
            "Run baseline-aware smoke on a cloned database.",
            "Set SOCMINT_ALLOW_REAL_DB_UPGRADE=YES_I_UNDERSTAND_REAL_DB_MIGRATION only for the controlled migration shell.",
            "Run alembic downgrade 0017_v12_10_schema_reconciliation only after approval.",
            "Verify /api/schema/status after rollback.",
        ],
        "command_template": "alembic downgrade 0017_v12_10_schema_reconciliation",
        "production_db_touched": False,
        "real_config_upgrade_run": False,
    }
