from pathlib import Path
import importlib.util
import json
import subprocess
import sys


SCRIPT = Path("scripts/final_release_readiness_manifest_v12_10_52.py")


def test_script_loads():
    spec = importlib.util.spec_from_file_location("readiness52", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    assert hasattr(mod, "main")


def test_final_readiness_manifest_generates():
    result = subprocess.run([sys.executable, str(SCRIPT)], text=True, capture_output=True)
    report = Path("release/final_readiness/FINAL_RELEASE_READINESS_MANIFEST_V12_10_52.json")
    assert report.exists()

    data = json.loads(report.read_text())
    assert data["production_db_touched"] is False
    assert data["real_config_upgrade_run"] is False
    assert data["schema_lock"] == "BASELINE_AWARE_DB_SMOKE_GO"
    assert "0018_approved_model_migration" in data["alembic_head"]

    if data["release_status"] == "PASS GO":
        assert result.returncode == 0
        assert data["errors"] == []
    else:
        assert result.returncode != 0
        assert data["errors"]
