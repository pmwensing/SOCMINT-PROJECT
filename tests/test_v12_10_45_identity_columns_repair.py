from pathlib import Path
import importlib.util
import json
import subprocess
import sys


SCRIPT = Path("scripts/repair_identity_columns_v12_10_45.py")


def load_module():
    assert SCRIPT.exists()
    spec = importlib.util.spec_from_file_location("identity_repair_v12_10_45", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_module_loads():
    mod = load_module()
    assert hasattr(mod, "patch_identity_columns")
    assert hasattr(mod, "duplicate_columns_in_table")


def test_identity_columns_repair_runs_safely():
    result = subprocess.run([sys.executable, str(SCRIPT)], text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr

    report = Path("release/db_smoke_identity_columns_repair/IDENTITY_COLUMNS_REPAIR_V12_10_45.json")
    assert report.exists()

    data = json.loads(report.read_text())
    assert data["schema_mutation"] == "none"
    assert data["production_db_touched"] is False
    assert data["real_config_upgrade_run"] is False
    assert data["repair_status"] == "GO"
    assert data["remaining_executable_todo"] == []
    assert data["duplicate_columns"] == []
