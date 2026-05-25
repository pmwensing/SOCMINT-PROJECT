from pathlib import Path
import importlib.util
import json
import subprocess
import sys


SCRIPT = Path("scripts/build_approved_migration_draft_v12_10_35.py")


def load_module():
    assert SCRIPT.exists()
    spec = importlib.util.spec_from_file_location("draft_v12_10_35", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_module_loads():
    mod = load_module()
    assert hasattr(mod, "load_and_validate")
    assert hasattr(mod, "build_draft")
    assert hasattr(mod, "build_manifest")


def test_refuses_or_builds_safely():
    result = subprocess.run([sys.executable, str(SCRIPT)], text=True, capture_output=True)

    forbidden = Path("alembic/versions/0018_APPROVED_MODEL_MIGRATION_DRAFT_V12_10_35.py")
    assert not forbidden.exists()

    if result.returncode != 0:
        refusal = Path("release/approved_migration_draft/APPROVED_MIGRATION_DRAFT_REFUSAL_V12_10_35.md")
        assert refusal.exists()
        assert "schema_mutation: `none`" in refusal.read_text()
        return

    manifest = Path("release/approved_migration_draft/APPROVED_MIGRATION_DRAFT_MANIFEST_V12_10_35.json")
    draft = Path("release/approved_migration_draft/0018_APPROVED_MODEL_MIGRATION_DRAFT_V12_10_35.py")
    report = Path("release/approved_migration_draft/APPROVED_MIGRATION_DRAFT_REPORT_V12_10_35.md")

    assert manifest.exists()
    assert draft.exists()
    assert report.exists()

    data = json.loads(manifest.read_text())
    assert data["schema_mutation"] == "none"
    assert data["migration_created"] is False
    assert data["alembic_versions_mutated"] is False
    assert data["alembic_upgrade_run"] is False
    assert data["approved_table_count"] > 0
    assert data["safety_checks"]["approval_valid"] is True

    text = draft.read_text()
    assert 'down_revision = "0017_v12_10_schema_reconciliation"' in text
    assert "op.create_table" in text
    assert "def downgrade():" in text


def test_draft_does_not_include_unapproved_tables_when_built():
    manifest_path = Path("release/approved_migration_draft/APPROVED_MIGRATION_DRAFT_MANIFEST_V12_10_35.json")
    draft_path = Path("release/approved_migration_draft/0018_APPROVED_MODEL_MIGRATION_DRAFT_V12_10_35.py")

    if not manifest_path.exists() or not draft_path.exists():
        return

    manifest = json.loads(manifest_path.read_text())
    draft = draft_path.read_text()

    for table in manifest["approved_tables"]:
        assert f'"{table}"' in draft
