import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "release" / "V35_0_PLANNING_CONTRACT.json"


def _contract():
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_v35_0_defines_complete_recovery_roadmap():
    contract = _contract()
    assert contract["schema"] == "socmint.v35.planning_contract.v35_0"
    assert contract["version"] == "v35.0.0"
    assert [item["slice"] for item in contract["roadmap"]] == [
        "v35.0",
        "v35.1",
        "v35.2",
        "v35.3",
        "v35.4",
        "v35.5",
        "v35.6",
        "v35.7",
    ]
    assert contract["roadmap"][0]["implemented"] is True
    assert all(item["implemented"] is False for item in contract["roadmap"][1:])
    assert contract["next_action"] == (
        "implement_v35_1_durable_confirmation_and_replay_ledger"
    )


def test_v35_0_is_planning_only_and_preserves_boundaries():
    contract = _contract()
    gate = contract["entry_gate"]
    boundaries = contract["scope_boundaries"]
    assert gate["planning_only"] is True
    assert gate["runtime_code_added"] is False
    assert gate["route_added"] is False
    assert gate["migration_added"] is False
    assert gate["v34_8_hardened_baseline_required"] is True
    assert all(value is False for value in boundaries.values())


def test_v35_0_requires_durable_recovery_invariants():
    invariants = _contract()["production_invariants"]
    assert all(value is True for value in invariants.values())


def test_v35_0_artifacts_and_hardened_dependencies_exist():
    for relative in (
        "release/V35_0_PLANNING_CONTRACT.json",
        "release/V35_0_ROADMAP_PRODUCTION_OBJECTIVE.md",
        "release/V35_0_EXISTING_CAPABILITY_INVENTORY.md",
        "release/V35_0_PLANNING_ENTRY_GATE.md",
        "release/V34_RELEASE_EVIDENCE.md",
        "release/V34_8_OPERATOR_ACCEPTANCE_AND_HARDENING.md",
        "src/socmint/governance_execution_hardening_v34_8.py",
    ):
        assert (ROOT / relative).exists(), relative
