from pathlib import Path
import importlib.util
import json
import subprocess
import sys


SCRIPT = Path("scripts/full_db_smoke_trace_capture_v12_10_48.py")


def load_module():
    assert SCRIPT.exists()
    spec = importlib.util.spec_from_file_location("trace48", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_module_loads():
    mod = load_module()
    assert hasattr(mod, "extract_exception_summary")
    assert hasattr(mod, "classify")


def test_trace_capture_generates_full_outputs_safely():
    result = subprocess.run([sys.executable, str(SCRIPT)], text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr

    report = Path("release/full_db_smoke_trace/FULL_DB_SMOKE_TRACE_CAPTURE_V12_10_48.json")
    assert report.exists()

    data = json.loads(report.read_text())
    assert data["schema_mutation"] == "temp_sqlite_only"
    assert data["production_db_touched"] is False
    assert data["real_config_upgrade_run"] is False
    assert Path(data["full_upgrade_output"]).exists()
    assert Path(data["full_sql_output"]).exists()
    assert "findings" in data
