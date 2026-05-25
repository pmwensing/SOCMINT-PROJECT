from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT = Path("scripts/fix_dashboard_route_registration_v12_10_54A.py")


def test_dashboard_route_fix_compiles():
    result = subprocess.run([sys.executable, str(SCRIPT)], text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr

    report = Path("release/v12_10_54A/DASHBOARD_ROUTE_FIX_V12_10_54A.json")
    data = json.loads(report.read_text())
    assert data["status"] == "GO"
    assert data["after_compile_ok"] is True
    assert data["production_db_touched"] is False
    assert data["real_config_upgrade_run"] is False


def test_v12_10_54_endpoints_after_dashboard_fix():
    from src.socmint.dashboard import app

    client = app.test_client()

    for path in [
        "/api/version",
        "/api/schema/status",
        "/api/schema/upgrade-guard",
        "/api/release/archive-integrity",
        "/api/schema/rollback/0018",
    ]:
        res = client.get(path)
        assert res.status_code == 200, path

    assert client.get("/api/version").get_json()["version"] == "12.10.54"
    assert client.get("/api/schema/status").get_json()["real_db_upgrade_default_blocked"] is True
    assert client.get("/api/schema/upgrade-guard").get_json()["allowed"] is False
