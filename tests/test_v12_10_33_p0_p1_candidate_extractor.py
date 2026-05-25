from pathlib import Path
import importlib.util
import json
import subprocess
import sys


SCRIPT = Path("scripts/extract_p0_p1_migration_candidates_v12_10_33.py")


def load_module():
    assert SCRIPT.exists()
    spec = importlib.util.spec_from_file_location("extractor_v12_10_33", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_extractor_module_loads():
    mod = load_module()
    assert hasattr(mod, "build_payload")
    assert hasattr(mod, "write_outputs")


def test_extractor_generates_review_only_outputs():
    subprocess.run([sys.executable, str(SCRIPT)], check=True)

    base = Path("release/p0_p1_migration_review")
    required = [
        "P0_P1_MIGRATION_CANDIDATES_V12_10_33.json",
        "P0_P1_MIGRATION_CANDIDATES_V12_10_33.csv",
        "P0_P1_MIGRATION_WORKSHEET_V12_10_33.md",
        "NON_EXECUTABLE_ALEMBIC_DRAFT_V12_10_33.py",
        "PASS_REVIEW_CLASSIFICATION_V12_10_33.md",
    ]

    for name in required:
        assert (base / name).exists(), name

    data = json.loads((base / "P0_P1_MIGRATION_CANDIDATES_V12_10_33.json").read_text())
    summary = data["summary"]

    assert summary["schema_mutation"] == "none"
    assert summary["migration_created"] is False
    assert summary["alembic_versions_mutated"] is False
    assert summary["candidate_count"] == summary["p0_count"] + summary["p1_count"]

    draft = (base / "NON_EXECUTABLE_ALEMBIC_DRAFT_V12_10_33.py").read_text()
    assert "NON-EXECUTABLE REVIEW DRAFT" in draft
    assert "raise RuntimeError" in draft
    assert not Path("alembic/versions/0018_REVIEW_ONLY_p0_p1_candidate_tables.py").exists()


def test_records_have_pass_review_classification():
    subprocess.run([sys.executable, str(SCRIPT)], check=True)
    data = json.loads(Path("release/p0_p1_migration_review/P0_P1_MIGRATION_CANDIDATES_V12_10_33.json").read_text())

    for record in data["records"]:
        assert record["priority_bucket"] in {"P0", "P1"}
        assert record["review"]["classification"] in {"PASS", "PASS_WITH_REVIEW_NOTES", "REVIEW"}
        assert "extracted" in record
