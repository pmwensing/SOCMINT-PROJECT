from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_runtime_discovery_report_import_path_hard_fix_passes():
    result = subprocess.run(
        [sys.executable, "scripts/runtime_app_discovery_report_v12_10_54D.py"],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    report = Path("release/v12_10_54D/RUNTIME_APP_DISCOVERY_REPORT_V12_10_54D.json")
    data = json.loads(report.read_text())

    assert data["status"] == "GO"
    assert data["endpoint_count"] == 5
    assert data["production_db_touched"] is False
    assert data["real_config_upgrade_run"] is False
    assert data["endpoint_results"]["/api/version"]["json"]["version"] == "12.10.54"
    assert data["endpoint_results"]["/api/schema/upgrade-guard"]["json"]["allowed"] is False
