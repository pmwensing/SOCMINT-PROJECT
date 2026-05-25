from pathlib import Path
import json
import subprocess
import sys


SCRIPT = Path("scripts/final_tag_manifest_head_sync_v12_10_53B.py")


def test_final_tag_manifest_head_sync_generates_report():
    result = subprocess.run([sys.executable, str(SCRIPT)], text=True, capture_output=True)

    report = Path("release/v12_10_53B/FINAL_TAG_MANIFEST_HEAD_SYNC_V12_10_53B.json")
    assert report.exists()

    data = json.loads(report.read_text())
    assert data["production_db_touched"] is False
    assert data["real_config_upgrade_run"] is False
    assert data["schema_lock"] == "BASELINE_AWARE_DB_SMOKE_GO"
    assert "0018_approved_model_migration" in data["alembic_head"]
    assert data["tarball_sha256"]
    assert data["zip_sha256"]

    if data["final_tag_ready"]:
        assert result.returncode == 0
        assert data["errors"] == []
    else:
        assert result.returncode != 0
        assert data["errors"]
