from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_production_entrypoint_report_direct_execution_import_path():
    result = subprocess.run(
        [sys.executable, "scripts/production_entrypoint_route_lock_report_v12_10_56.py"],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    report = Path("release/v12_10_56/PRODUCTION_ENTRYPOINT_ROUTE_LOCK_V12_10_56.json")
    data = json.loads(report.read_text())

    assert data["status"] == "GO"
    assert data["selected_spec"] == "src.socmint.wsgi:app"
    assert data["verification_mode"] == "production_entrypoint"
    assert data["production_db_touched"] is False
    assert data["real_config_upgrade_run"] is False
