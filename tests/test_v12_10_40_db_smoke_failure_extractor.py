from pathlib import Path
import importlib.util
import json
import subprocess
import sys


SCRIPT = Path("scripts/db_smoke_failure_extractor_v12_10_40.py")


def load_module():
    assert SCRIPT.exists()
    spec = importlib.util.spec_from_file_location("failure_v12_10_40", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_module_loads():
    mod = load_module()
    assert hasattr(mod, "classify")
    assert hasattr(mod, "affected_lines")


def test_failure_extractor_generates_reports():
    subprocess.run([sys.executable, str(SCRIPT)], check=True)

    report = Path("release/db_smoke_failure/DB_SMOKE_FAILURE_EXTRACTOR_V12_10_40.json")
    assert report.exists()

    data = json.loads(report.read_text())
    assert data["schema_mutation"] == "none"
    assert data["production_db_touched"] is False
    assert data["real_config_upgrade_run"] is False
    assert "findings" in data
    assert Path("release/db_smoke_failure/DB_SMOKE_REPAIR_TARGETS_V12_10_40.md").exists()
