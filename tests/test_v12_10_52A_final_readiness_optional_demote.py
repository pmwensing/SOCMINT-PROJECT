from pathlib import Path
import json
import subprocess
import sys


SCRIPT = Path("scripts/final_readiness_optional_demote_v12_10_52A.py")


def test_optional_demote_generates_corrected_manifest():
    result = subprocess.run([sys.executable, str(SCRIPT)], text=True, capture_output=True)

    manifest = Path("release/final_readiness/FINAL_RELEASE_READINESS_MANIFEST_V12_10_52A.json")
    assert manifest.exists()

    data = json.loads(manifest.read_text())
    assert data["production_db_touched"] is False
    assert data["real_config_upgrade_run"] is False
    assert data["schema_lock"] == "BASELINE_AWARE_DB_SMOKE_GO"
    assert "0018_approved_model_migration" in data["alembic_head"]
    assert data["canonical_ok"] is True

    if data["release_status"] == "PASS GO":
        assert result.returncode == 0
        assert data["hard_failure_count"] == 0
    else:
        assert result.returncode != 0
        assert data["hard_failure_count"] > 0
