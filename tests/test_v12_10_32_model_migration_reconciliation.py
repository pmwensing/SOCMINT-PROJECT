from pathlib import Path
import csv
import importlib.util
import json
import subprocess
import sys


SCRIPT = Path("scripts/model_migration_reconciliation_audit_v12_10_32.py")


def load_module():
    assert SCRIPT.exists()
    spec = importlib.util.spec_from_file_location("recon_v12_10_32", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_reconciliation_module_loads():
    mod = load_module()
    assert hasattr(mod, "extract_model_tables")
    assert hasattr(mod, "extract_migration_tables")
    assert hasattr(mod, "build_reconciliation")


def test_reconciliation_generates_reports_without_schema_mutation():
    subprocess.run([sys.executable, str(SCRIPT)], check=True)

    json_path = Path("release/model_migration_reconciliation/MODEL_MIGRATION_RECONCILIATION_V12_10_32.json")
    md_path = Path("release/model_migration_reconciliation/MODEL_MIGRATION_RECONCILIATION_V12_10_32.md")
    csv_path = Path("release/model_migration_reconciliation/MODEL_MIGRATION_RECONCILIATION_V12_10_32.csv")
    plan_path = Path("release/model_migration_reconciliation/ALEMBIC_CANDIDATE_PLAN_V12_10_32.md")

    assert json_path.exists()
    assert md_path.exists()
    assert csv_path.exists()
    assert plan_path.exists()

    data = json.loads(json_path.read_text())
    assert data["summary"]["schema_mutation"] == "none"
    assert data["summary"]["migration_created"] is False
    assert "missing_records" in data
    assert isinstance(data["missing_records"], list)

    with csv_path.open() as f:
        rows = list(csv.DictReader(f))
    assert isinstance(rows, list)

    plan = plan_path.read_text()
    assert "This is a **plan only**" in plan
    assert "def upgrade():" in plan
    assert "pass" in plan


def test_reconciliation_records_have_required_fields():
    subprocess.run([sys.executable, str(SCRIPT)], check=True)

    data = json.loads(Path("release/model_migration_reconciliation/MODEL_MIGRATION_RECONCILIATION_V12_10_32.json").read_text())

    for record in data["missing_records"][:25]:
        for key in [
            "table",
            "domain",
            "status",
            "priority_bucket",
            "priority_score",
            "migration_action",
            "sources",
            "indirect_coverage_hints",
        ]:
            assert key in record
