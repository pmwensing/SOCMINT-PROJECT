from pathlib import Path
import configparser
import importlib.util
import json
import subprocess
import sys


SCRIPT = Path("scripts/promote_approved_migration_v12_10_37.py")


def active_versions_dir() -> Path:
    cfg = configparser.ConfigParser()
    cfg.read("alembic.ini")
    script_location = cfg.get("alembic", "script_location", fallback="alembic")
    return Path(script_location) / "versions"


def promoted_path() -> Path:
    return active_versions_dir() / "0018_approved_model_migration.py"


def load_module():
    assert SCRIPT.exists()
    spec = importlib.util.spec_from_file_location("promote_v12_10_37", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_module_loads():
    mod = load_module()
    assert hasattr(mod, "promote")
    assert hasattr(mod, "sanitize_draft")
    assert hasattr(mod, "validate_alembic_head")
    assert hasattr(mod, "active_alembic_versions_dir")


def test_promotes_without_schema_upgrade():
    result = subprocess.run([sys.executable, str(SCRIPT)], text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr

    promoted = promoted_path()
    manifest = Path("release/migration_promotion/MIGRATION_PROMOTION_MANIFEST_V12_10_37.json")
    report = Path("release/migration_promotion/MIGRATION_PROMOTION_REPORT_V12_10_37.md")

    assert promoted.exists()
    assert manifest.exists()
    assert report.exists()

    text = promoted.read_text()
    assert 'revision = "0018_approved_model_migration"' in text
    assert 'down_revision = "0017_v12_10_schema_reconciliation"' in text
    assert "op.create_table" in text
    assert "op.drop_table" in text
    assert "TODO" in text
    assert "RuntimeError" not in text

    data = json.loads(manifest.read_text())
    assert data["schema_mutation"] == "none"
    assert data["alembic_upgrade_run"] is False
    assert data["promoted"] is True
    assert data["promoted_path"] == str(promoted.resolve()) or data["promoted_path"] == str(promoted)
    assert data["alembic"]["expected_head_present"] is True


def test_alembic_sees_0018_head_after_promotion():
    result = subprocess.run(["alembic", "heads"], text=True, capture_output=True)
    assert result.returncode == 0
    assert "0018_approved_model_migration" in result.stdout
