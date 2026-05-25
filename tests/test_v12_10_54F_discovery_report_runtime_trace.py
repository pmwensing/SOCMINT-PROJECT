from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_direct_runtime_discovery_report_passes_with_trace_file():
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
    assert data["expected_endpoint_count"] == 5
    assert data["production_db_touched"] is False
    assert data["real_config_upgrade_run"] is False

    assert data["endpoint_results"]["/api/version"]["json"]["version"] == "12.10.54"
    assert data["endpoint_results"]["/api/schema/status"]["json"]["real_db_upgrade_default_blocked"] is True
    assert data["endpoint_results"]["/api/schema/upgrade-guard"]["json"]["allowed"] is False
    assert data["endpoint_results"]["/api/release/archive-integrity"]["json"]["integrity_ok"] is True
    assert data["endpoint_results"]["/api/schema/rollback/0018"]["json"]["rollback_to"] == "0017_v12_10_schema_reconciliation"

    assert Path(data["trace_file"]).exists()
