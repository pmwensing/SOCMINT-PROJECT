from pathlib import Path
import json
import subprocess
import sys


SCRIPT = Path("scripts/release_package_tag_manifest_v12_10_53.py")


def test_release_package_manifest_generates():
    result = subprocess.run([sys.executable, str(SCRIPT)], text=True, capture_output=True)

    manifest = Path("release/v12_10_53/RELEASE_ARTIFACT_MANIFEST_V12_10_53.json")
    tag_manifest = Path("release/v12_10_53/TAG_MANIFEST_V12_10_53.json")
    tarball = Path("dist/SOCMINT-PROJECT-v12.10.53-release.tar.gz")
    zipfile = Path("dist/SOCMINT-PROJECT-v12.10.53-release.zip")

    assert manifest.exists()
    assert tag_manifest.exists()
    assert tarball.exists()
    assert zipfile.exists()

    data = json.loads(manifest.read_text())
    assert data["production_db_touched"] is False
    assert data["real_config_upgrade_run"] is False
    assert "0018_approved_model_migration" in data["alembic_head"]
    assert data["schema_lock"] == "BASELINE_AWARE_DB_SMOKE_GO"
    assert data["archives"]["tarball"]["sha256"]
    assert data["archives"]["zip"]["sha256"]

    if data["release_status"] == "PASS GO":
        assert result.returncode == 0
        assert data["errors"] == []
    else:
        assert result.returncode != 0
        assert data["errors"]
