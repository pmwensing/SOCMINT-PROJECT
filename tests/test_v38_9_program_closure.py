import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "release/V38_9_PROGRAM_CLOSURE_CONTRACT.json"
PILOT_PATH = ROOT / "release/V38_9_CONTROLLED_FICTIONAL_PILOT.json"
CLOSURE_PATH = ROOT / "release/V38_9_PROGRAM_CLOSURE.md"
EVIDENCE_PATH = ROOT / "release/V38_RELEASE_EVIDENCE.md"


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_v38_9_contract_closes_the_complete_program():
    contract = _json(CONTRACT_PATH)
    assert contract["schema"] == "socmint.v38.program_closure.v38_9"
    assert contract["version"] == "v38.9.0"
    assert contract["status"] == "closed"
    assert contract["closure_only"] is True
    for key in (
        "runtime_added_in_v38_9",
        "route_added_in_v38_9",
        "migration_added_in_v38_9",
        "network_behavior_changed_in_v38_9",
        "authority_changed_in_v38_9",
    ):
        assert contract[key] is False

    assert [item["slice"] for item in contract["slice_merge_ledger"]] == [
        "v38.0",
        "v38.1",
        "v38.2",
        "v38.3",
        "v38.4",
        "v38.5",
        "v38.6",
        "v38.6.1",
        "v38.6.2",
        "v38.6.3",
        "v38.6.4",
        "v38.7",
        "v38.8",
    ]
    assert len({item["pr"] for item in contract["slice_merge_ledger"]}) == 13
    assert all(len(item["head_sha"]) == 40 for item in contract["slice_merge_ledger"])
    assert all(len(item["merge_sha"]) == 40 for item in contract["slice_merge_ledger"])
    assert contract["final_delivery"]["slice"] == "v38.8"
    assert contract["final_delivery"]["pr"] == 330
    assert contract["final_delivery"]["validation"]["all_green"] is True

    assert contract["controlled_pilot"]["status"] == "passed"
    assert contract["controlled_pilot"]["real_case_evidence_used"] is False
    assert contract["controlled_pilot"]["real_third_party_crawl_performed"] is False
    assert contract["controlled_pilot"]["production_live_collection_performed"] is False
    assert all(contract["authoritative_reuse_preserved"].values())
    assert all(contract["program_invariants"].values())
    assert all(value is False for value in contract["prohibited_automation"].values())

    closure = contract["closure"]
    assert closure["v38_closed"] is True
    assert closure["planned_slices_complete"] is True
    assert closure["remaining_v38_runtime_work"] is False
    assert closure["remaining_v38_route_work"] is False
    assert closure["remaining_v38_schema_or_migration_work"] is False
    assert closure["remaining_v38_network_adapter_work"] is False
    assert closure["next_runtime_requires_new_planning_and_compatibility_gate"] is True
    assert (
        closure["next_action"]
        == "open_new_program_planning_gate_before_additional_runtime_work"
    )
    assert contract["closure_validation"]["status"] in {
        "pending_exact_head_validation",
        "complete",
    }


def test_v38_9_controlled_pilot_is_fictional_complete_and_grounded():
    pilot = _json(PILOT_PATH)
    assert pilot["schema"] == "socmint.v38.controlled_fictional_pilot.v38_9"
    assert pilot["status"] == "passed"
    assert pilot["validation_checkpoint"]["all_green"] is True
    assert len(pilot["scenarios"]) == 9
    assert all(item["status"] == "passed" for item in pilot["scenarios"])
    proof_paths = {
        proof
        for scenario in pilot["scenarios"]
        for proof in scenario["proof_files"]
    }
    assert len(proof_paths) >= 14
    missing = [path for path in sorted(proof_paths) if not (ROOT / path).is_file()]
    assert missing == []
    assert all(value is False for value in pilot["pilot_invariants"].values())
    assert pilot["result"]["pre_live_network_governance_proven"] is True
    assert pilot["result"]["capture_provenance_and_handoff_proven"] is True
    assert pilot["result"]["duplicate_change_and_relevance_controls_proven"] is True
    assert pilot["result"]["read_only_workspace_and_browser_safety_proven"] is True
    assert pilot["result"]["production_live_collection_performed_by_pilot"] is False


def test_v38_9_closure_documents_record_safety_and_no_remaining_work():
    closure = CLOSURE_PATH.read_text(encoding="utf-8").lower()
    evidence = EVIDENCE_PATH.read_text(encoding="utf-8").lower()
    for marker in (
        "v38 is complete and closed",
        "documentation-and-test-only",
        "no v38 runtime, route, schema, migration, network-adapter, workspace, pilot, or closure work remains",
        "new program planning and compatibility gate",
        "no automatic artifact acceptance",
        "no automatic source-independence assessment",
        "no automatic observation promotion",
        "no automatic truth assignment",
        "no automatic entity merge",
        "no automatic claim approval",
        "no automatic dossier mutation",
        "no automatic import staging",
        "no automatic export or publication",
    ):
        assert marker in closure
    for marker in (
        "v38.0",
        "v38.6.4",
        "v38.8",
        "controlled fictional pilot",
        "ci 4531",
        "full verification 1194",
        "legacy readiness 2491",
        "browser e2e 184",
    ):
        assert marker in evidence


def test_v38_9_introduces_no_runtime_route_or_migration_file():
    src_matches = [
        path
        for path in (ROOT / "src/socmint").rglob("*")
        if path.is_file() and "v38_9" in path.name.lower()
    ]
    migration_roots = [ROOT / "migrations", ROOT / "alembic"]
    migration_matches = [
        path
        for base in migration_roots
        if base.exists()
        for path in base.rglob("*")
        if path.is_file() and "v38_9" in path.name.lower()
    ]
    assert src_matches == []
    assert migration_matches == []
