from pathlib import Path
import importlib.util
import json
import subprocess
import sys


SCRIPT = Path("scripts/db_smoke_result_gate_v12_10_39.py")


def load_module():
    assert SCRIPT.exists()
    spec = importlib.util.spec_from_file_location("gate_v12_10_39", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_gate_module_loads():
    mod = load_module()
    assert hasattr(mod, "build_gate")
    assert hasattr(mod, "classify_errors")


def test_gate_generates_report_and_preserves_safety():
    result = subprocess.run([sys.executable, str(SCRIPT)], text=True, capture_output=True)

    report = Path("release/db_smoke_gate/DB_SMOKE_RESULT_GATE_V12_10_39.json")
    assert report.exists()

    data = json.loads(report.read_text())
    assert data["production_db_touched"] is False
    assert data["real_config_upgrade_run"] is False
    assert data["temp_sqlite_only"] is True
    assert data["db_smoke_status"] in {"GO", "NO-GO"}

    if data["db_smoke_status"] == "GO":
        assert result.returncode == 0
        assert data["release_status"] == "PASS GO"
        assert Path("release/db_smoke_gate/PROMOTION_READY_MANIFEST_V12_10_39.json").exists()
    else:
        assert result.returncode != 0
        assert data["release_status"] in {"HOLD", "BLOCKED"}
        assert Path("release/db_smoke_gate/DB_SMOKE_REPAIR_PLAN_V12_10_39.md").exists()
