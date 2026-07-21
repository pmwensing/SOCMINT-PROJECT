import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "release/V37_9_PROGRAM_CLOSURE_CONTRACT.json"
CLOSURE_PATH = ROOT / "release/V37_9_PROGRAM_CLOSURE.md"
EVIDENCE_PATH = ROOT / "release/V37_RELEASE_EVIDENCE.md"


def _contract():
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_v37_9_closes_complete_program_and_records_exact_delivery():
    contract = _contract()
    assert contract["schema"] == "socmint.v37.program_closure.v37_9"
    assert contract["version"] == "v37.9.0"
    assert contract["status"] == "closed"
    assert contract["closure"]["v37_closed"] is True
    assert contract["closure"]["runtime_work_remaining_in_v37"] is False
    assert contract["closure"]["schema_or_migration_work_remaining_in_v37"] is False
    assert [item["slice"] for item in contract["delivered_slices"]] == [
        f"v37.{index}" for index in range(10)
    ]
    assert [item["pull_request"] for item in contract["slice_merges"]] == list(
        range(307, 316)
    )
    assert contract["final_delivery"] == {
        "pull_request": 315,
        "validated_head_sha": "7bb00b7516c87af7d85128402d634609c5226efd",
        "merge_sha": "a9e53695a2db374791904aa56f6264770058d387",
    }


def test_v37_9_records_green_final_validation_and_safety_invariants():
    contract = _contract()
    assert contract["validation"] == {
        "ci": {"run": 4432, "status": "success"},
        "full_verification": {"run": 1150, "status": "success"},
        "legacy_v12_10_19": {"run": 2447, "status": "success"},
        "browser_e2e": {"run": 180, "status": "success"},
    }
    assert all(value is True for value in contract["production_invariants"].values())
    assert all(value is False for value in contract["prohibited_automation"].values())


def test_v37_9_closure_documents_preserve_program_boundaries():
    closure = CLOSURE_PATH.read_text(encoding="utf-8").lower()
    evidence = EVIDENCE_PATH.read_text(encoding="utf-8").lower()
    for marker in (
        "operator-provided export",
        "single-record",
        "read-only",
        "no v37 runtime or schema work remains",
        "new planning and compatibility gate",
    ):
        assert marker in closure
    for marker in (
        "no real case evidence",
        "export readiness from export or publication",
        "browser e2e: **180**",
        "a9e53695a2db374791904aa56f6264770058d387",
    ):
        assert marker in evidence


def test_v37_9_is_documentation_and_test_only():
    prohibited = [
        path
        for path in ROOT.rglob("*v37_9*")
        if path.is_file()
        and (
            "src/socmint" in path.as_posix()
            or "migrations" in path.as_posix()
            or "alembic" in path.as_posix()
            or "scripts" in path.as_posix()
        )
    ]
    assert prohibited == []
