from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_app_adapter_discovers_hardened_app():
    from src.socmint.v12_10_54_app_adapter import get_hardened_dashboard_app

    app = get_hardened_dashboard_app()
    client = app.test_client()

    expected = [
        "/api/version",
        "/api/schema/status",
        "/api/schema/upgrade-guard",
        "/api/release/archive-integrity",
        "/api/schema/rollback/0018",
    ]

    for path in expected:
        res = client.get(path)
        assert res.status_code == 200, path

    assert client.get("/api/version").get_json()["version"] == "12.10.54"
    assert client.get("/api/schema/status").get_json()["real_db_upgrade_default_blocked"] is True
    assert client.get("/api/schema/upgrade-guard").get_json()["allowed"] is False


def test_runtime_app_discovery_report_passes():
    result = subprocess.run(
        [sys.executable, "scripts/runtime_app_discovery_report_v12_10_54D.py"],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    report = Path("release/v12_10_54D/RUNTIME_APP_DISCOVERY_REPORT_V12_10_54D.json")
    data = json.loads(report.read_text())
    assert data["status"] == "GO"
    assert data["production_db_touched"] is False
    assert data["real_config_upgrade_run"] is False
