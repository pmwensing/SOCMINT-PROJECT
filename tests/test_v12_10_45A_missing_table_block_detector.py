from pathlib import Path
import importlib.util
import json
import subprocess
import sys


SCRIPT = Path("scripts/missing_table_block_detector_v12_10_45A.py")


def load_module():
    assert SCRIPT.exists()
    spec = importlib.util.spec_from_file_location("missing_table_detector_v12_10_45A", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_module_loads():
    mod = load_module()
    assert hasattr(mod, "extract_create_tables")
    assert hasattr(mod, "active_migration")


def test_detector_generates_report_safely():
    result = subprocess.run([sys.executable, str(SCRIPT)], text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr

    report = Path("release/missing_table_block_detector/MISSING_TABLE_BLOCK_DETECTOR_V12_10_45A.json")
    assert report.exists()

    data = json.loads(report.read_text())
    assert data["schema_mutation"] == "none"
    assert data["production_db_touched"] is False
    assert data["real_config_upgrade_run"] is False
    assert "missing_create_blocks" in data
    assert "structural_missing" in data
