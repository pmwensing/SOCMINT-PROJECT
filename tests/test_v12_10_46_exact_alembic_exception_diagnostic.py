from pathlib import Path
import importlib.util
import json
import subprocess
import sys


SCRIPT = Path("scripts/exact_alembic_exception_diagnostic_v12_10_46.py")


def load_module():
    assert SCRIPT.exists()
    spec = importlib.util.spec_from_file_location("diag46", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_module_loads():
    mod = load_module()
    assert hasattr(mod, "find_create_table_block")
    assert hasattr(mod, "table_pattern_scan")


def test_diagnostic_generates_reports_safely():
    result = subprocess.run([sys.executable, str(SCRIPT)], text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr

    report = Path("release/exact_alembic_exception/EXACT_ALEMBIC_EXCEPTION_DIAGNOSTIC_V12_10_46.json")
    assert report.exists()

    data = json.loads(report.read_text())
    assert data["schema_mutation"] == "none"
    assert data["production_db_touched"] is False
    assert data["real_config_upgrade_run"] is False
    assert "findings" in data
    assert data["target_blocks"]["all_tab_identity_cols"]["found"] is True
    assert data["target_blocks"]["identity_columns"]["found"] is True
