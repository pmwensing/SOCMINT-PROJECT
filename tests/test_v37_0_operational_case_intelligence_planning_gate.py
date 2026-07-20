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
        "v37.0",
        "v37.1",
        "v37.2",
        "v37.3",
        "v37.4",
        "v37.5",
        "v37.6",
        "v37.7",
        "v37.8",
        "v37.9",
    ]
    assert contract["runtime_gate"] == {
        "runtime_implemented_in_v37_0": False,
        "migration_implemented_in_v37_0": False,
        "runtime_allowed_after_v37_0_merge": True,
        "next_action": "implement_v37_1_case_scoped_import_envelopes",
    }


def test_v37_0_reuses_existing_authorities_and_blocks_duplication():
    contract = _contract()
    assert set(contract["authoritative_reuse"]) == {
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
    assert all(value is False for value in contract["prohibited_duplication"].values())
    assert all(value is False for value in contract["prohibited_automation"].values())
    assert all(value is True for value in contract["production_invariants"].values())


def test_v37_0_required_baselines_and_case_foundation_exist():
    contract = _contract()
    assert (ROOT / contract["required_baselines"]["v36_closure_contract"]).exists()
    closure = json.loads(
        (ROOT / contract["required_baselines"]["v36_closure_contract"]).read_text(
            encoding="utf-8"
        )
    )
    assert closure["closure"]["v36_closed"] is True
    for relative_path in contract["required_baselines"]["case_foundation_paths_required"]:
        assert (ROOT / relative_path).exists(), relative_path


def test_v37_0_planning_documents_preserve_non_duplication_language():
    roadmap = ROADMAP_PATH.read_text(encoding="utf-8")
    inventory = INVENTORY_PATH.read_text(encoding="utf-8")
    ownership = OWNERSHIP_PATH.read_text(encoding="utf-8")
    gate = ENTRY_GATE_PATH.read_text(encoding="utf-8")
    assert "tool export → preserved artifact" in roadmap
    assert "synthetic fixtures" in roadmap
    assert "no parallel case registry" in ownership
    assert "no second artifact vault" in ownership
    assert "no second observation authority" in ownership
    assert "no mutable canonical fact or truth table" in ownership
    assert "no alternate dossier product pipeline" in ownership
    assert "no alternate export or publication authority" in ownership
    assert "running collection tools automatically" in inventory
    assert "v37.0 is planning-only" in gate
    assert "implement_v37_1_case_scoped_import_envelopes" in gate


def test_v37_0_introduces_no_runtime_or_migration_files():
    prohibited = [
        path
        for path in ROOT.rglob("*v37_0*")
        if path.is_file()
        and (
            "src/socmint" in path.as_posix()
            or "migrations" in path.as_posix()
            or "alembic" in path.as_posix()
        )
    ]
    assert prohibited == []
