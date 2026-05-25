from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_runtime_mount_status_verifies_routes():
    from src.socmint.v12_10_55_runtime_mount import runtime_mount_status

    result = runtime_mount_status()

    assert result["status"] == "GO"
    assert result["production_db_touched"] is False
    assert result["real_config_upgrade_run"] is False

    required = {
        "/api/version",
        "/api/schema/status",
        "/api/schema/upgrade-guard",
        "/api/release/archive-integrity",
        "/api/schema/rollback/0018",
    }
    assert required.issubset(set(result["v12_10_54_routes"]))

    assert result["verification"]["endpoint_results"]["/api/version"]["json"]["version"] == "12.10.54"
    assert result["verification"]["endpoint_results"]["/api/schema/status"]["json"]["real_db_upgrade_default_blocked"] is True
    assert result["verification"]["endpoint_results"]["/api/schema/upgrade-guard"]["json"]["allowed"] is False


def test_real_runtime_route_mount_report_generates():
    result = subprocess.run(
        [sys.executable, "scripts/real_runtime_route_mount_report_v12_10_55.py"],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    report = Path("release/v12_10_55/REAL_RUNTIME_ROUTE_MOUNT_REPORT_V12_10_55.json")
    data = json.loads(report.read_text())

    assert data["status"] == "GO"
    assert data["production_db_touched"] is False
    assert data["real_config_upgrade_run"] is False
    assert len(data["v12_10_54_routes"]) == 5
