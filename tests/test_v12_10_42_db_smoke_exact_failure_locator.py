from pathlib import Path
import importlib.util
import json
import subprocess
import sys


SCRIPT = Path("scripts/db_smoke_exact_failure_locator_v12_10_42.py")


def load_module():
    assert SCRIPT.exists()
    spec = importlib.util.spec_from_file_location("locator_v12_10_42", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_module_loads():
    mod = load_module()
    assert hasattr(mod, "extract_table_blocks")
    assert hasattr(mod, "infer_probable_failing_table")


def test_locator_generates_report():
    subprocess.run([sys.executable, str(SCRIPT)], check=True)

    report = Path("release/db_smoke_exact_failure/DB_SMOKE_EXACT_FAILURE_LOCATOR_V12_10_42.json")
    assert report.exists()

    data = json.loads(report.read_text())
    assert data["schema_mutation"] == "none"
    assert data["production_db_touched"] is False
    assert data["real_config_upgrade_run"] is False
    assert "probable_failing_table" in data
    assert Path("release/db_smoke_exact_failure/DB_SMOKE_FAILED_TABLE_REPAIR_TARGET_V12_10_42.md").exists()
    assert Path("release/db_smoke_exact_failure/FAILING_UPGRADE_OUTPUT_V12_10_42.txt").exists()
