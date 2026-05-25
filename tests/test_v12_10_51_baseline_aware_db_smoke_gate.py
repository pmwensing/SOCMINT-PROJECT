from pathlib import Path
import importlib.util
import json
import subprocess
import sys


SCRIPT = Path("scripts/baseline_aware_db_smoke_gate_v12_10_51.py")


def load_module():
    assert SCRIPT.exists()
    spec = importlib.util.spec_from_file_location("baseaware51", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_module_loads():
    mod = load_module()
    assert hasattr(mod, "sqlite_tables")
    assert hasattr(mod, "alembic_version")


def test_baseline_aware_gate_runs_safely():
    result = subprocess.run([sys.executable, str(SCRIPT)], text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr

    report = Path("release/baseline_aware_db_smoke/BASELINE_AWARE_DB_SMOKE_GATE_V12_10_51.json")
    assert report.exists()

    data = json.loads(report.read_text())
    assert data["schema_mutation"] == "temp_sqlite_only"
    assert data["production_db_touched"] is False
    assert data["real_config_upgrade_run"] is False
    assert data["status"] == "GO"
    assert data["release_status"] == "PASS GO"
    assert data["version_after_upgrade"] == "0018_approved_model_migration"
    assert data["version_after_downgrade"] == "0017_v12_10_schema_reconciliation"
    assert data["missing_after_upgrade"] == []
    assert data["owned_lingering_after_downgrade"] == []
    assert data["baseline_missing_after_downgrade"] == []
