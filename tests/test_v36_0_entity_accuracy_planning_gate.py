import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "release" / "V36_0_ENTITY_ACCURACY_PLANNING_CONTRACT.json"


def _contract():
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_v36_0_defines_complete_entity_accuracy_roadmap():
    contract = _contract()
    assert contract["schema"] == "socmint.v36.planning_contract.v36_0"
    assert contract["version"] == "v36.0.0"
    assert [item["slice"] for item in contract["roadmap"]] == [
        "v36.0",
        "v36.1",
        "v36.2",
        "v36.3",
        "v36.4",
        "v36.5",
        "v36.6",
        "v36.7",
        "v36.8",
    ]
    assert contract["roadmap"][0]["implemented"] is True
    assert all(item["implemented"] is False for item in contract["roadmap"][1:])
    assert contract["next_action"] == (
        "implement_v36_1_source_registry_and_capture_integrity_after_v35_closure"
    )


def test_v36_0_is_planning_only_and_requires_v35_closure_for_runtime():
    gate = _contract()["entry_gate"]
    assert gate["planning_only"] is True
    assert gate["runtime_code_added"] is False
    assert gate["route_added"] is False
    assert gate["migration_added"] is False
    assert gate["v30_closed_baseline_required"] is True
    assert gate["v35_4_hardened_baseline_required"] is True
    assert gate["v35_program_closure_required_before_v36_1"] is True


def test_v36_0_preserves_non_duplication_and_safety_boundaries():
    boundaries = _contract()["scope_boundaries"]
    assert all(value is False for value in boundaries.values())
    assert boundaries["automatic_truth_assignment"] is False
    assert boundaries["automatic_entity_merge"] is False
    assert boundaries["automatic_claim_approval"] is False
    assert boundaries["automatic_dossier_mutation"] is False
    assert boundaries["privacy_gate_bypass"] is False


def test_v36_0_requires_source_grounded_review_invariants():
    invariants = _contract()["production_invariants"]
    assert all(value is True for value in invariants.values())
    assert invariants["identity_confidence_is_separate_from_factual_support"]
    assert invariants["dependent_sources_do_not_inflate_corroboration"]
    assert invariants["contradictions_and_rejected_hypotheses_are_preserved"]
    assert invariants["dossier_contribution_requires_a_separate_explicit_decision"]


def test_v36_0_reuses_authoritative_existing_layers():
    reuse = _contract()["authoritative_reuse"]
    assert set(reuse) == {
        "spine_pipeline",
        "evidence_and_observations",
        "analytic_claims_and_reviews",
        "audit_history",
        "entity_graph",
        "dossier_outputs",
        "governance_execution",
    }
    assert reuse["audit_history"] == "existing append-only AuditLog"


def test_v36_0_artifacts_and_authoritative_dependencies_exist():
    for relative in (
        "release/V36_0_ENTITY_ACCURACY_PLANNING_CONTRACT.json",
        "release/V36_0_ENTITY_ACCURACY_ROADMAP.md",
        "release/V36_0_EXISTING_CAPABILITY_INVENTORY.md",
        "release/V36_0_SCHEMA_OWNERSHIP_MAP.md",
        "release/V36_0_PLANNING_ENTRY_GATE.md",
        "docs/SOCMINT_DOSSIER_SPINE_SPEC.md",
        "release/V30_0_ROADMAP_PRODUCTION_OBJECTIVE.md",
        "src/socmint/analytic_confidence_v30_4.py",
        "src/socmint/human_analytic_review_v30_5.py",
        "src/socmint/analytic_dossier_contribution_v30_6.py",
        "src/socmint/identity_graph.py",
        "src/socmint/dossier_builder_v3.py",
        "src/socmint/dossier_traceability.py",
        "src/socmint/dossier_quality_gate.py",
        "release/V35_0_PLANNING_CONTRACT.json",
    ):
        assert (ROOT / relative).exists(), relative


def test_v36_0_schema_map_forbids_parallel_truth_stores():
    schema_map = (
        ROOT / "release" / "V36_0_SCHEMA_OWNERSHIP_MAP.md"
    ).read_text(encoding="utf-8")
    assert "no parallel case registry" in schema_map
    assert "no second artifact vault" in schema_map
    assert "no mutable canonical fact table" in schema_map
    assert "no opaque truth score" in schema_map
    assert "no alternate dossier product pipeline" in schema_map
    assert "reproducible projections" in schema_map
