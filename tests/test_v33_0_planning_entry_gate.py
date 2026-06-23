import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "release" / "V33_0_PLANNING_CONTRACT.json"


def _contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_v33_0_defines_complete_workspace_roadmap():
    contract = _contract()

    assert contract["schema"] == "socmint.v33.planning_contract.v33_0"
    assert contract["version"].startswith("v33.")
    assert contract["program"] == (
        "Operational Dissemination Governance Workspace and "
        "Case-Centric Command Surface"
    )
    assert contract["primary_workspace"] == (
        "Case-Centric Dissemination Command Surface"
    )
    assert [item["slice"] for item in contract["roadmap"]] == [
        "v33.0",
        "v33.1",
        "v33.2",
        "v33.3",
        "v33.4",
        "v33.5",
        "v33.6",
        "v33.7",
    ]
    assert contract["roadmap"][0]["implemented"] is True
    assert all(
        isinstance(item["implemented"], bool)
        for item in contract["roadmap"]
    )
    assert str(contract["next_action"]).startswith(
        ("implement_v33_", "run_v33_7_", "prepare_v33_")
    )


def test_v33_0_preserves_planning_boundaries_across_runtime_slices():
    contract = _contract()
    entry_gate = contract["entry_gate"]
    boundaries = contract["scope_boundaries"]

    assert isinstance(entry_gate["runtime_code_added"], bool)
    assert isinstance(entry_gate["route_added"], bool)
    assert entry_gate["migration_added"] is False
    assert boundaries["parallel_governance_backend"] is False
    assert boundaries["automatic_external_transmission"] is False
    assert boundaries["automatic_authorization_or_recall"] is False
    assert boundaries["published_or_historical_record_mutation"] is False
    assert boundaries["destructive_retention"] is False
    assert boundaries["secret_or_endpoint_exposure"] is False


def test_v33_0_reuses_v32_and_existing_case_surface():
    contract = _contract()
    invariants = contract["production_invariants"]

    assert invariants["v32_contracts_remain_authoritative"] is True
    assert invariants["workspace_is_case_scoped"] is True
    assert invariants["workspace_is_read_first"] is True
    assert invariants["actions_delegate_to_existing_v32_services"] is True
    assert invariants[
        "browser_and_api_views_share_one_canonical_read_model"
    ] is True

    for relative_path in (
        "release/V33_0_ROADMAP_PRODUCTION_OBJECTIVE.md",
        "release/V33_0_EXISTING_CAPABILITY_INVENTORY.md",
        "release/V33_0_PLANNING_ENTRY_GATE.md",
        "release/V32_0_PLANNING_CONTRACT.json",
        "src/socmint/dissemination_product_review_v32_7.py",
        "src/socmint/recall_retention_lifecycle_v32_6.py",
    ):
        assert (ROOT / relative_path).exists(), relative_path
