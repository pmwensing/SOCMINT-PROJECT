from pathlib import Path
import importlib.util
import json
import subprocess
import sys


SCRIPT = Path("scripts/existing_table_collision_guard_v12_10_49.py")


def load_module():
    assert SCRIPT.exists()
    spec = importlib.util.spec_from_file_location("collision49", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_module_loads():
    mod = load_module()
    assert hasattr(mod, "baseline_0017_tables")
    assert hasattr(mod, "patch_collision_tables")


def test_collision_guard_runs_safely():
    result = subprocess.run([sys.executable, str(SCRIPT)], text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr

    report = Path("release/existing_table_collision_guard/EXISTING_TABLE_COLLISION_GUARD_V12_10_49.json")
    assert report.exists()

    data = json.loads(report.read_text())
    assert data["schema_mutation"] == "none"
    assert data["production_db_touched"] is False
    assert data["real_config_upgrade_run"] is False
    assert data["guard_status"] == "GO"
    assert "spine_connector_runs" in data["collision_tables"]
