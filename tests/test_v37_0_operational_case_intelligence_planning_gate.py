import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "release/V37_0_OPERATIONAL_CASE_INTELLIGENCE_PLANNING_CONTRACT.json"
ROADMAP_PATH = ROOT / "release/V37_0_OPERATIONAL_CASE_INTELLIGENCE_ROADMAP.md"
INVENTORY_PATH = ROOT / "release/V37_0_EXISTING_CAPABILITY_INVENTORY.md"
OWNERSHIP_PATH = ROOT / "release/V37_0_SCHEMA_OWNERSHIP_MAP.md"
ENTRY_GATE_PATH = ROOT / "release/V37_0_PLANNING_ENTRY_GATE.md"


def _contract():
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_v37_0_planning_contract_declares_complete_roadmap():
    contract = _contract()
    assert contract["schema"] == "socmint.v37.planning_contract.v37_0"
    assert contract["planning_only"] is True
    assert [item["slice"] for item in contract["roadmap"]] == [
        f"v37.{index}" for index in range(10)
    ]
    gate = contract["runtime_gate"]
    assert gate["runtime_implemented_in_v37_0"] is False
    assert gate["migration_implemented_in_v37_0"] is False
    assert gate["runtime_allowed_after_v37_0_merge"] is True
    assert gate["next_action"] == "implement_v37_1_case_scoped_import_envelopes"


def test_v37_0_reuses_existing_authorities_and_blocks_duplication():
    contract = _contract()
    required_authorities = {
        "case_scope_and_privacy",
        "collection_contracts",
        "artifact_evidence",
        "source_registry",
        "canonical_observations",
        "entity_resolution",
        "source_independence",
        "claim_verification",
        "relationships",
        "dossier_synthesis",
        "human_review",
        "dossier_contribution",
        "export_and_publication",
        "audit",
    }
    assert required_authorities.issubset(contract["authoritative_reuse"])
    assert contract["prohibited_duplication"]
    assert all(value is False for value in contract["prohibited_duplication"].values())
    assert contract["prohibited_automation"]
    assert all(value is False for value in contract["prohibited_automation"].values())
    assert contract["production_invariants"]
    assert all(value is True for value in contract["production_invariants"].values())


def test_v37_0_required_baselines_and_case_foundation_exist():
    contract = _contract()
    closure_path = ROOT / contract["required_baselines"]["v36_closure_contract"]
    assert closure_path.is_file()
    closure = json.loads(closure_path.read_text(encoding="utf-8"))
    assert closure["status"] == "closed"
    assert closure["closure"]["v36_closed"] is True
    required_paths = contract["required_baselines"]["case_foundation_paths_required"]
    assert required_paths
    missing = [path for path in required_paths if not (ROOT / path).is_file()]
    assert missing == []


def test_v37_0_planning_documents_preserve_safety_boundaries():
    roadmap = ROADMAP_PATH.read_text(encoding="utf-8").lower()
    inventory = INVENTORY_PATH.read_text(encoding="utf-8").lower()
    ownership = OWNERSHIP_PATH.read_text(encoding="utf-8").lower()
    gate = ENTRY_GATE_PATH.read_text(encoding="utf-8").lower()
    for marker in (
        "tool export",
        "preserved artifact",
        "synthetic fixtures",
        "no automatic observation promotion",
    ):
        assert marker in roadmap
    for marker in (
        "no parallel case registry",
        "no second artifact vault",
        "no second observation authority",
        "no mutable canonical fact or truth table",
        "no alternate dossier product pipeline",
        "no alternate export or publication authority",
    ):
        assert marker in ownership
    assert "running collection tools automatically" in inventory
    assert "v37.0 is planning-only" in gate
    assert "implement_v37_1_case_scoped_import_envelopes" in gate


def test_v37_0_introduces_no_runtime_or_migration_files():
    runtime_matches = [
        path
        for path in (ROOT / "src/socmint").rglob("*")
        if path.is_file() and "v37_0" in path.name.lower()
    ]
    migration_roots = [ROOT / "migrations", ROOT / "alembic"]
    migration_matches = [
        path
        for base in migration_roots
        if base.exists()
        for path in base.rglob("*")
        if path.is_file() and "v37_0" in path.name.lower()
    ]
    assert runtime_matches == []
    assert migration_matches == []
