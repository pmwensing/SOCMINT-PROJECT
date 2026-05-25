from pathlib import Path
import importlib.util
import json
import subprocess
import sys


SCRIPT = Path("scripts/db_migration_smoke_v12_10_38.py")


def load_module():
    assert SCRIPT.exists()
    spec = importlib.util.spec_from_file_location("smoke_v12_10_38", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_module_loads():
    mod = load_module()
    assert hasattr(mod, "main")
    assert hasattr(mod, "make_temp_alembic_config")
    assert hasattr(mod, "sqlite_tables")


def test_smoke_generates_report_and_never_touches_real_db():
    result = subprocess.run([sys.executable, str(SCRIPT)], text=True, capture_output=True)

    report_path = Path("release/db_migration_smoke/DB_MIGRATION_SMOKE_V12_10_38.json")
    assert report_path.exists()

    data = json.loads(report_path.read_text())
    assert data["production_db_touched"] is False
    assert data["real_config_upgrade_run"] is False
    assert data["schema_mutation"] == "temp_sqlite_only"
    assert "temp_db_path" in data

    # Smoke may be GO or NO-GO. NO-GO is valid if the promoted migration
    # still has SQLite incompatibilities. The point is to catch this safely.
    assert data["smoke_status"] in {"GO", "NO-GO"}

    if data["smoke_status"] == "GO":
        assert result.returncode == 0
        assert data["version_after_upgrade"] == "0018_approved_model_migration"
        assert data["version_after_downgrade"] == "0017_v12_10_schema_reconciliation"
        assert data["missing_after_upgrade"] == []
        assert data["lingering_after_downgrade"] == []
    else:
        assert result.returncode != 0
        assert data["errors"]


def test_no_alembic_upgrade_head_against_real_config_in_script():
    text = SCRIPT.read_text()
    assert '["alembic", "upgrade", "head"]' not in text
    assert '"real_config_upgrade_run": False' in text
