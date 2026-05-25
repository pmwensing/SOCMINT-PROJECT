from pathlib import Path
import importlib.util
import json
import subprocess
import sys


SCRIPT = Path("scripts/iterative_db_smoke_repair_loop_v12_10_44.py")


def load_module():
    assert SCRIPT.exists()
    spec = importlib.util.spec_from_file_location("loop_v12_10_44", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_module_loads():
    mod = load_module()
    assert hasattr(mod, "main")
    assert hasattr(mod, "smoke_status")
    assert hasattr(mod, "safety_assert")


def test_loop_generates_report_and_preserves_safety():
    result = subprocess.run([sys.executable, str(SCRIPT)], text=True, capture_output=True)

    report = Path("release/db_smoke_repair_loop/ITERATIVE_DB_SMOKE_REPAIR_LOOP_V12_10_44.json")
    assert report.exists()

    data = json.loads(report.read_text())
    assert data["schema_mutation"] == "temp_sqlite_only"
    assert data["production_db_touched"] is False
    assert data["real_config_upgrade_run"] is False
    assert data["release_status"] in {"PASS GO", "HOLD"}

    if data["release_status"] == "PASS GO":
        assert result.returncode == 0
        assert data["final"]["smoke_status"] == "GO"
    else:
        assert result.returncode != 0
        assert data["final"]["smoke_status"] == "NO-GO"
