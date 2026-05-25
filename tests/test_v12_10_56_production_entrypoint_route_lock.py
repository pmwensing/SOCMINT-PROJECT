from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_production_entrypoint_status_go():
    from src.socmint.v12_10_56_production_entrypoint import production_entrypoint_status

    result = production_entrypoint_status()

    assert result["status"] == "GO"
    assert result["verification_mode"] == "production_entrypoint"
    assert result["selected_spec"]
    assert result["production_db_touched"] is False
    assert result["real_config_upgrade_run"] is False

    required = {
        "/api/version",
        "/api/schema/status",
        "/api/schema/upgrade-guard",
        "/api/release/archive-integrity",
        "/api/schema/rollback/0018",
    }
    assert required.issubset(set(result["selected_verification"]["v12_10_54_routes"]))


def test_production_entrypoint_route_lock_report_generates():
    result = subprocess.run(
        [sys.executable, "scripts/production_entrypoint_route_lock_report_v12_10_56.py"],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    report = Path("release/v12_10_56/PRODUCTION_ENTRYPOINT_ROUTE_LOCK_V12_10_56.json")
    data = json.loads(report.read_text())

    assert data["status"] == "GO"
    assert data["verification_mode"] == "production_entrypoint"
    assert data["selected_spec"]
    assert data["production_db_touched"] is False
    assert data["real_config_upgrade_run"] is False
