import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "release/V37_0_OPERATIONAL_CASE_INTELLIGENCE_PLANNING_CONTRACT.json"


def _contract():
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_v37_0_contract_is_planning_only_and_complete():
    contract = _contract()
    assert contract["schema"] == "socmint.v37.planning_contract.v37_0"
    assert contract["version"] == "v37.0.0"
    assert contract["status"] == "planning_gate"
    assert contract["planning_only"] is True
    assert [item["slice"] for item in contract["roadmap"]] == [
        f"v37.{index}" for index in range(10)
    ]
    gate = contract["runtime_gate"]
    assert gate["runtime_implemented_in_v37_0"] is False
    assert gate["migration_implemented_in_v37_0"] is False
    assert gate["next_action"] == "implement_v37_1_case_scoped_import_envelopes"


def test_v37_0_contract_preserves_authorities_and_safety_boundaries():
    contract = _contract()
    assert len(contract["authoritative_reuse"]) >= 14
    assert all(value is False for value in contract["prohibited_duplication"].values())
    assert all(value is False for value in contract["prohibited_automation"].values())
    assert all(value is True for value in contract["production_invariants"].values())


def test_v37_0_required_baselines_and_planning_artifacts_exist():
    contract = _contract()
    closure_path = ROOT / contract["required_baselines"]["v36_closure_contract"]
    closure = json.loads(closure_path.read_text(encoding="utf-8"))
    assert closure["status"] == "closed"
    assert closure["closure"]["v36_closed"] is True
    for relative_path in contract["required_baselines"]["case_foundation_paths_required"]:
        assert (ROOT / relative_path).is_file(), relative_path
    for relative_path in (
        "release/V37_0_OPERATIONAL_CASE_INTELLIGENCE_ROADMAP.md",
        "release/V37_0_EXISTING_CAPABILITY_INVENTORY.md",
        "release/V37_0_SCHEMA_OWNERSHIP_MAP.md",
        "release/V37_0_PLANNING_ENTRY_GATE.md",
    ):
        assert (ROOT / relative_path).is_file(), relative_path
