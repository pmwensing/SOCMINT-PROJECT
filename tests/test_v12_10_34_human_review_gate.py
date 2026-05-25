from pathlib import Path
import importlib.util
import json
import subprocess
import sys


SCRIPT = Path("scripts/human_review_gate_v12_10_34.py")


def load_module():
    assert SCRIPT.exists()
    spec = importlib.util.spec_from_file_location("gate_v12_10_34", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_gate_module_loads():
    mod = load_module()
    assert hasattr(mod, "run_generate")
    assert hasattr(mod, "run_approve")
    assert hasattr(mod, "run_refuse_migration")


def test_generate_outputs_without_schema_mutation():
    subprocess.run([sys.executable, str(SCRIPT), "generate"], check=True)

    base = Path("release/human_review_gate")
    required = [
        "HUMAN_REVIEW_CHECKLIST_V12_10_34.md",
        "HUMAN_REVIEW_CHECKLIST_V12_10_34.csv",
        "REVIEW_QUEUES_V12_10_34.json",
        "APPROVAL_LIST_TEMPLATE_V12_10_34.json",
        "approval_list.json",
        "MIGRATION_CREATION_REFUSAL_V12_10_34.md",
        "HUMAN_REVIEW_GATE_SUMMARY_V12_10_34.json",
        "HUMAN_REVIEW_GATE_SUMMARY_V12_10_34.md",
    ]

    for name in required:
        assert (base / name).exists(), name

    summary = json.loads((base / "HUMAN_REVIEW_GATE_SUMMARY_V12_10_34.json").read_text())
    assert summary["schema_mutation"] == "none"
    assert summary["migration_created"] is False
    assert summary["alembic_versions_mutated"] is False
    assert summary["refused_to_create_executable_migration"] is True

    queues = json.loads((base / "REVIEW_QUEUES_V12_10_34.json").read_text())
    assert "PASS" in queues["queues"]
    assert "PASS_WITH_REVIEW_NOTES" in queues["queues"]
    assert "REVIEW" in queues["queues"]

    assert not Path("alembic/versions/0018_REVIEW_ONLY_p0_p1_candidate_tables.py").exists()


def test_refuse_migration_mode_does_not_create_alembic_revision():
    subprocess.run([sys.executable, str(SCRIPT), "refuse-migration"], check=True)
    assert not Path("alembic/versions/0018_REVIEW_ONLY_p0_p1_candidate_tables.py").exists()


def test_approve_requires_valid_metadata_and_builds_approved_set(tmp_path):
    subprocess.run([sys.executable, str(SCRIPT), "generate"], check=True)

    approval = Path("release/human_review_gate/approval_list.json")
    data = json.loads(approval.read_text())

    candidates = json.loads(Path("release/p0_p1_migration_review/P0_P1_MIGRATION_CANDIDATES_V12_10_33.json").read_text())
    pass_tables = [
        r["table"] for r in candidates["records"]
        if r["review"]["classification"] == "PASS"
    ]

    data["approved_by"] = "test-human-review"
    data["approval_date"] = "2026-05-24"
    data["approved_tables"] = pass_tables[:2]
    data["notes"] = "test approval for gate validation"

    approval.write_text(json.dumps(data, indent=2, sort_keys=True))

    subprocess.run([sys.executable, str(SCRIPT), "approve"], check=True)

    approved_set = Path("release/human_review_gate/approved_migration_set.json")
    assert approved_set.exists()

    approved = json.loads(approved_set.read_text())
    assert approved["schema_mutation"] == "none"
    assert approved["migration_created"] is False
    assert approved["alembic_versions_mutated"] is False
    assert approved["validation"]["valid"] is True
    assert approved["validation"]["approved_table_count"] == 2
