from pathlib import Path
import json
import subprocess
import sys


SCRIPT = Path("scripts/post_commit_package_refresh_v12_10_53A.py")


def test_post_commit_package_refresh_generates_tag_ready_manifest():
    result = subprocess.run([sys.executable, str(SCRIPT)], text=True, capture_output=True)

    manifest = Path("release/v12_10_53A/TAG_READY_MANIFEST_V12_10_53A.json")
    report = Path("release/v12_10_53A/POST_COMMIT_PACKAGE_REFRESH_REPORT_V12_10_53A.md")

    assert manifest.exists()
    assert report.exists()

    data = json.loads(manifest.read_text())
    assert data["production_db_touched"] is False
    assert data["real_config_upgrade_run"] is False
    assert data["schema_lock"] == "BASELINE_AWARE_DB_SMOKE_GO"
    assert "0018_approved_model_migration" in data["alembic_head"]
    assert data["tarball_sha256"]
    assert data["zip_sha256"]

    if data["tag_ready"]:
        assert result.returncode == 0
        assert data["errors"] == []
        assert data["manifest_commit"] == data["current_short"]
    else:
        assert result.returncode != 0
        assert data["errors"]
