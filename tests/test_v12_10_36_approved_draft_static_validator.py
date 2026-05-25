from pathlib import Path
import json
import subprocess
import sys

SCRIPT = Path("scripts/validate_approved_migration_draft_v12_10_36.py")


def test_validator_script_exists():
    assert SCRIPT.exists()


def test_validator_generates_report_without_schema_mutation():
    result = subprocess.run([sys.executable, str(SCRIPT)], text=True, capture_output=True)

    report = Path("release/approved_draft_validation/APPROVED_DRAFT_STATIC_VALIDATION_V12_10_36.json")
    assert report.exists()

    data = json.loads(report.read_text())
    assert data["schema_mutation"] == "none"
    assert data["migration_created"] is False
    assert data["alembic_versions_mutated"] is False
    assert data["alembic_upgrade_run"] is False
    assert data["approved_table_count"] == data["create_table_count"] == data["drop_table_count"]
    assert data["drop_tables"] == list(reversed(data["create_tables"]))
    assert data["todo_count"] >= 0
    assert not Path("alembic/versions/0018_APPROVED_MODEL_MIGRATION_DRAFT_V12_10_35.py").exists()
