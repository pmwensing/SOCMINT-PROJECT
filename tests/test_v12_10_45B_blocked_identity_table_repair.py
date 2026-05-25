from pathlib import Path
import importlib.util
import json
import subprocess
import sys


SCRIPT = Path("scripts/repair_blocked_identity_tables_v12_10_45B.py")


def load_module():
    assert SCRIPT.exists()
    spec = importlib.util.spec_from_file_location("blocked_identity_repair_v12_10_45B", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_module_loads():
    mod = load_module()
    assert hasattr(mod, "patch_table")
    assert hasattr(mod, "duplicate_active_columns")


def test_blocked_identity_repair_runs_safely():
    result = subprocess.run([sys.executable, str(SCRIPT)], text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr

    report = Path("release/blocked_identity_table_repair/BLOCKED_IDENTITY_TABLE_REPAIR_V12_10_45B.json")
    assert report.exists()

    data = json.loads(report.read_text())
    assert data["schema_mutation"] == "none"
    assert data["production_db_touched"] is False
    assert data["real_config_upgrade_run"] is False
    assert data["repair_status"] == "GO"
    assert data["remaining_executable_todo"] == []
    assert data["found_tables"]["all_tab_identity_cols"] is True
    assert data["found_tables"]["identity_columns"] is True
