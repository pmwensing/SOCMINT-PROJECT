from pathlib import Path
import importlib.util
import json
import subprocess
import sys


SCRIPT = Path("scripts/downgrade_symmetry_repair_v12_10_50.py")


def load_module():
    assert SCRIPT.exists()
    spec = importlib.util.spec_from_file_location("downrepair50", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_module_loads():
    mod = load_module()
    assert hasattr(mod, "repair_downgrade")
    assert hasattr(mod, "extract_active_drop_tables")


def test_downgrade_repair_runs_safely():
    result = subprocess.run([sys.executable, str(SCRIPT)], text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr

    report = Path("release/downgrade_symmetry_repair/DOWNGRADE_SYMMETRY_REPAIR_V12_10_50.json")
    assert report.exists()

    data = json.loads(report.read_text())
    assert data["schema_mutation"] == "none"
    assert data["production_db_touched"] is False
    assert data["real_config_upgrade_run"] is False
    assert data["repair_status"] == "GO"
    assert data["missing_after_repair"] == []
