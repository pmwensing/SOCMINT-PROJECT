import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "release" / "V35_6_PROGRAM_CLOSURE_CONTRACT.json"


def _contract():
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_v35_6_formally_closes_program_and_hands_off_to_v36():
    contract = _contract()
    assert contract["schema"] == "socmint.v35.program_closure.v35_6"
    assert contract["version"] == "v35.6.0"
    assert contract["status"] == "closed"
    assert contract["closure"]["v35_closed"] is True
    assert contract["closure"]["runtime_work_remaining_in_v35"] is False
    assert contract["closure"]["next_action"] == (
        "merge_v36_0_entity_accuracy_planning_gate"
    )


def test_v35_6_records_exact_runtime_merge_and_validation_evidence():
    contract = _contract()
    delivery = contract["final_delivery"]
    assert delivery == {
        "pull_request": 289,
        "validated_head_sha": "3916532caebf02ca9350ab098716215c83bf1b71",
        "squash_merge_sha": "f1b750241d03217aed0cb2a2fa255c7c9e5f37ee",
    }
    assert contract["validation"] == {
        "ci": {"run": 4187, "status": "success"},
        "full_verification": {"run": 1066, "status": "success"},
        "legacy_v12_10_19": {"run": 2399, "status": "success"},
        "browser_e2e": {"run": 168, "status": "success"},
    }


def test_v35_6_preserves_no_retry_and_append_only_invariants():
    contract = _contract()
    resolution = contract["roadmap_resolution"]
    invariants = contract["production_invariants"]
    assert resolution["safe_retry_controls_implemented"] is False
    assert resolution["automatic_retry_implemented"] is False
    assert resolution["planned_v35_7_separate_slice_required"] is False
    assert all(value is True for value in invariants.values())
    assert invariants["automatic_retry_remains_disabled"] is True
    assert invariants["historical_audit_records_are_append_only"] is True


def test_v35_6_delivered_slices_are_complete_and_ordered():
    assert [item["slice"] for item in _contract()["delivered_slices"]] == [
        "v35.0",
        "v35.1",
        "v35.2",
        "v35.3",
        "v35.4",
        "v35.5",
        "v35.6",
    ]


def test_v35_6_release_artifacts_and_authoritative_layers_exist():
    for relative in (
        "release/V35_6_PROGRAM_CLOSURE_CONTRACT.json",
        "release/V35_6_PROGRAM_CLOSURE.md",
        "release/V35_RELEASE_EVIDENCE.md",
        "src/socmint/durable_execution_ledger_v35_1.py",
        "src/socmint/action_contract_registry_v35_2.py",
        "src/socmint/action_contract_validation_v35_2.py",
        "src/socmint/governance_execution_result_model_v35_3.py",
        "src/socmint/governance_execution_result_store_v35_3.py",
        "src/socmint/execution_reconciliation_service_v35_4.py",
        "src/socmint/execution_reconciliation_read_v35_4.py",
        "src/socmint/execution_recovery_observability_v35_5.py",
        "src/socmint/execution_recovery_observability_routes_v35_5.py",
    ):
        assert (ROOT / relative).exists(), relative


def test_v35_release_evidence_does_not_claim_retry_delivery():
    evidence = (ROOT / "release" / "V35_RELEASE_EVIDENCE.md").read_text(
        encoding="utf-8"
    )
    assert "Automatic retry remains disabled." in evidence
    assert "Uncertain work is not silently replayed." in evidence
    assert "v35 is closed." in evidence
