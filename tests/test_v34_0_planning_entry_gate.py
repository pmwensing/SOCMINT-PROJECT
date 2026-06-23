import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "release" / "V34_0_PLANNING_CONTRACT.json"


def _contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_v34_0_defines_complete_execution_workspace_roadmap():
    contract = _contract()

    assert contract["schema"] == "socmint.v34.planning_contract.v34_0"
    assert contract["version"].startswith("v34.")
    assert contract["program"] == (
        "Operational Case Governance Actions and Human-Confirmed "
        "Execution Workspace"
    )
    assert contract["primary_workspace"] == (
        "Human-Confirmed Case Governance Action Workspace"
    )
    assert [item["slice"] for item in contract["roadmap"]] == [
        "v34.0",
        "v34.1",
        "v34.2",
        "v34.3",
        "v34.4",
        "v34.5",
        "v34.6",
        "v34.7",
    ]
    assert contract["roadmap"][0]["implemented"] is True
    assert all(
        isinstance(item["implemented"], bool)
        for item in contract["roadmap"]
    )
    assert str(contract["next_action"]).startswith(
        ("implement_v34_", "run_v34_", "prepare_v34_")
    )


def test_v34_0_preserves_execution_boundaries_across_runtime_slices():
    contract = _contract()
    gate = contract["entry_gate"]
    boundaries = contract["scope_boundaries"]

    assert isinstance(gate["runtime_code_added"], bool)
    assert isinstance(gate["route_added"], bool)
    assert gate["migration_added"] is False

    for boundary in (
        "automatic_action_execution",
        "parallel_execution_backend",
        "direct_transport_logic_in_workspace",
        "duplicate_governance_persistence",
        "v32_validation_or_transition_bypass",
        "action_without_explicit_confirmation",
        "bulk_delivery_recall_or_retention_by_default",
        "published_or_historical_record_mutation",
        "secret_or_endpoint_exposure",
        "case_access_change",
        "migration_allowed_without_proven_schema_gap",
    ):
        assert boundaries[boundary] is False


def test_v34_0_requires_authoritative_human_confirmed_delegation():
    contract = _contract()
    invariants = contract["production_invariants"]

    required_true = (
        "v32_services_remain_authoritative",
        "v33_workspace_remains_canonical_read_surface",
        "actions_are_case_scoped",
        "every_action_resolves_one_authoritative_delegate",
        "every_mutating_action_requires_explicit_human_confirmation",
        "eligibility_is_checked_before_confirmation",
        "confirmation_payload_is_deterministically_summarized",
        "execution_result_identifies_authoritative_audit_record",
        "workspace_refreshes_after_authoritative_execution",
        "idempotency_or_replay_protection_is_required",
        "authorization_delivery_feedback_recall_and_retention_boundaries_remain_distinct",
        "no_raw_secret_material_is_rendered",
        "browser_and_api_actions_share_one_canonical_contract",
        "failed_or_blocked_actions_do_not_mutate_state",
        "bulk_actions_are_unavailable_without_separate_reviewed_contract",
    )
    for invariant in required_true:
        assert invariants[invariant] is True


def test_v34_0_planning_artifacts_and_dependencies_exist():
    for relative_path in (
        "release/V34_0_PLANNING_CONTRACT.json",
        "release/V34_0_ROADMAP_PRODUCTION_OBJECTIVE.md",
        "release/V34_0_EXISTING_CAPABILITY_INVENTORY.md",
        "release/V34_0_PLANNING_ENTRY_GATE.md",
        "release/V33_0_PLANNING_CONTRACT.json",
        "src/socmint/case_centric_operator_workspace_v33_6.py",
        "src/socmint/case_centric_operator_workspace_routes_v33_6.py",
        "src/socmint/dissemination_product_review_v32_7.py",
    ):
        assert (ROOT / relative_path).exists(), relative_path
