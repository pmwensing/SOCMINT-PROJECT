import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "release" / "V32_0_PLANNING_CONTRACT.json"


def _contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_v32_0_defines_complete_program_roadmap():
    contract = _contract()

    assert contract["schema"] == "socmint.v32.planning_contract.v32_0"
    assert contract["version"].startswith("v32.")
    assert contract["primary_workspace"] == "Dissemination Governance Workspace"
    assert [item["slice"] for item in contract["roadmap"]] == [
        "v32.0",
        "v32.1",
        "v32.2",
        "v32.3",
        "v32.4",
        "v32.5",
        "v32.6",
        "v32.7",
    ]
    assert contract["roadmap"][0]["implemented"] is True
    assert all(isinstance(item["implemented"], bool) for item in contract["roadmap"])
    assert str(contract["next_action"]).startswith("implement_v32_")


def test_v32_0_entry_gate_boundaries_remain_enforced_after_runtime_slices():
    contract = _contract()
    entry_gate = contract["entry_gate"]
    boundaries = contract["scope_boundaries"]

    assert entry_gate["roadmap_defined"] is True
    assert entry_gate["existing_capability_inventory_defined"] is True
    assert isinstance(entry_gate["runtime_code_added"], bool)
    assert isinstance(entry_gate["route_added"], bool)
    assert entry_gate["migration_added"] is False
    assert boundaries["automatic_external_transmission"] is False
    assert boundaries["automatic_recipient_authorization"] is False
    assert boundaries["automatic_release_approval"] is False
    assert boundaries["published_revision_mutation"] is False
    assert boundaries["prior_delivery_record_mutation"] is False


def test_v32_0_requires_reuse_of_v22_and_v31_primitives():
    contract = _contract()
    invariants = contract["production_invariants"]

    assert invariants[
        "immutable_published_revision_is_the_only_distributable_source"
    ] is True
    assert invariants["existing_v22_distribution_primitives_are_reused"] is True
    assert invariants["existing_v31_publication_primitives_are_reused"] is True
    assert invariants["human_authorization_required_before_dissemination"] is True
    assert invariants["delivery_attempts_and_receipts_are_append_only"] is True
    assert invariants["recipient_feedback_is_separate_from_source_intelligence"] is True

    for relative_path in (
        "release/V32_0_ROADMAP_PRODUCTION_OBJECTIVE.md",
        "release/V32_0_EXISTING_CAPABILITY_INVENTORY.md",
        "src/socmint/immutable_published_revision_v31_5.py",
        "src/socmint/publication_supersession_v31_6.py",
        "src/socmint/dossier_release_authorization_v22_1.py",
        "src/socmint/dossier_secure_distribution_v22_3.py",
    ):
        assert (ROOT / relative_path).exists(), relative_path
