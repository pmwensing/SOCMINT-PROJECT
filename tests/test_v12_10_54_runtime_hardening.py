from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def test_runtime_guard_blocks_real_db_upgrade_by_default():
    env = os.environ.copy()
    env.pop("SOCMINT_ALLOW_REAL_DB_UPGRADE", None)
    result = subprocess.run(
        [sys.executable, "scripts/real_db_upgrade_guard_v12_10_54.py"],
        text=True,
        capture_output=True,
        env=env,
    )
    assert result.returncode == 1
    data = json.loads(result.stdout)
    assert data["allowed"] is False
    assert data["production_db_touched"] is False
    assert data["real_config_upgrade_run"] is False


def test_runtime_guard_allows_only_explicit_operator_confirmation():
    env = os.environ.copy()
    env["SOCMINT_ALLOW_REAL_DB_UPGRADE"] = "YES_I_UNDERSTAND_REAL_DB_MIGRATION"
    result = subprocess.run(
        [sys.executable, "scripts/real_db_upgrade_guard_v12_10_54.py"],
        text=True,
        capture_output=True,
        env=env,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["allowed"] is True
    assert data["production_db_touched"] is False
    assert data["real_config_upgrade_run"] is False


def test_archive_integrity_report_passes():
    result = subprocess.run(
        [sys.executable, "scripts/release_archive_integrity_v12_10_54.py"],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    data = json.loads(result.stdout)
    assert data["integrity_ok"] is True
    assert data["production_db_touched"] is False
    assert data["real_config_upgrade_run"] is False


def test_post_release_runtime_hardening_report_passes():
    result = subprocess.run(
        [sys.executable, "scripts/post_release_runtime_hardening_report_v12_10_54.py"],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    data = json.loads(result.stdout)
    assert data["release_status"] == "PASS GO"
    assert data["real_db_upgrade_blocked_by_default"] is True
    assert data["production_db_touched"] is False
    assert data["real_config_upgrade_run"] is False


def test_flask_runtime_endpoints_registered():
    from src.socmint.v12_10_54_app_adapter import get_hardened_dashboard_app

    app = get_hardened_dashboard_app()

    client = app.test_client()

    res = client.get("/api/version")
    assert res.status_code == 200
    assert res.get_json()["version"] == "12.10.54"

    res = client.get("/api/schema/status")
    assert res.status_code == 200
    body = res.get_json()
    assert body["real_db_upgrade_default_blocked"] is True
    assert body["production_db_touched"] is False
    assert body["real_config_upgrade_run"] is False

    res = client.get("/api/schema/upgrade-guard")
    assert res.status_code == 200
    assert res.get_json()["allowed"] is False

    res = client.get("/api/release/archive-integrity")
    assert res.status_code == 200
    assert res.get_json()["integrity_ok"] is True

    res = client.get("/api/schema/rollback/0018")
    assert res.status_code == 200
    assert res.get_json()["rollback_to"] == "0017_v12_10_schema_reconciliation"
