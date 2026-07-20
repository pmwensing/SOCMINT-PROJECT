import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "release" / "V36_9_PROGRAM_CLOSURE_CONTRACT.json"
CLOSURE = ROOT / "release" / "V36_9_PROGRAM_CLOSURE.md"
EVIDENCE = ROOT / "release" / "V36_RELEASE_EVIDENCE.md"


def _contract():
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_v36_9_formally_closes_the_complete_program():
    contract = _contract()
    assert contract["schema"] == "socmint.v36.program_closure.v36_9"
    assert contract["version"] == "v36.9.0"
    assert contract["status"] == "closed"
    assert contract["closed_at"] == "2026-07-20"
    assert [item["slice"] for item in contract["delivered_slices"]] == [
        "v36.0",
        "v36.1",
        "v36.2",
        "v36.3",
        "v36.4",
        "v36.5",
        "v36.6",
        "v36.7",
        "v36.8",
        "v36.9",
    ]
    assert contract["closure"] == {
        "v36_closed": True,
        "runtime_work_remaining_in_v36": False,
        "schema_or_migration_work_remaining_in_v36": False,
        "next_program": "unassigned",
        "next_action": (
            "define_the_next_program_planning_and_compatibility_gate_before_runtime_work"
        ),
    }


def test_v36_9_records_exact_slice_merges():
    merges = {item["slice"]: item for item in _contract()["slice_merges"]}
    assert set(merges) == {
        "v36.0",
        "v36.1",
        "v36.2",
        "v36.3",
        "v36.4",
        "v36.5",
        "v36.6",
        "v36.7",
        "v36.8",
    }
    assert merges["v36.0"] == {
        "slice": "v36.0",
        "pull_request": 294,
        "merge_sha": "dfbaee61f65832f9475cd386dc74389f865e5248",
    }
    assert merges["v36.4"]["pull_request"] == 298
    assert merges["v36.4"]["merge_sha"] == (
        "a84c2bdd7a57af242203ab1eb9ca74ff1e3be7d5"
    )
    assert merges["v36.8"] == {
        "slice": "v36.8",
        "pull_request": 304,
        "merge_sha": "94bb889e3cda2e378a57190eac0d1a50714eb800",
    }


def test_v36_9_records_final_exact_head_validation():
    contract = _contract()
    assert contract["final_delivery"] == {
        "pull_request": 304,
        "validated_head_sha": "6aa600ea0623a1af52faad3955a521c22bdf9a09",
        "merge_sha": "94bb889e3cda2e378a57190eac0d1a50714eb800",
    }
    assert contract["validation"] == {
        "ci": {"run": 4310, "status": "success"},
        "full_verification": {"run": 1091, "status": "success"},
        "legacy_v12_10_19": {"run": 2421, "status": "success"},
        "browser_e2e": {"run": 172, "status": "success"},
    }


def test_v36_9_preserves_production_invariants_and_prohibitions():
    contract = _contract()
    assert all(contract["production_invariants"].values())
    assert all(value is False for value in contract["prohibited_automation"].values())
    assert contract["production_invariants"][
        "dependent_sources_do_not_inflate_corroboration"
    ]
    assert contract["production_invariants"][
        "human_analytic_review_remains_required_for_consequential_use"
    ]
    assert contract["production_invariants"][
        "entity_accuracy_workspace_is_read_only"
    ]


def test_v36_9_authoritative_runtime_and_release_artifacts_exist():
    required = (
        "release/V36_0_ENTITY_ACCURACY_PLANNING_CONTRACT.json",
        "release/V36_1_SOURCE_REGISTRY_CAPTURE_INTEGRITY.md",
        "release/V36_2_CANONICAL_OBSERVATION_CONTRACT.md",
        "release/V36_3_ENTITY_CANDIDATE_RESOLUTION.md",
        "release/V36_4_SOURCE_INDEPENDENCE_GRAPH.md",
        "release/V36_5_CLAIM_VERIFICATION_ALTERNATIVE_RANKING.md",
        "release/V36_6_RELATIONSHIP_TIMELINE_VERIFICATION.md",
        "release/V36_7_VERSIONED_DOSSIER_SYNTHESIS.md",
        "release/V36_8_ENTITY_ACCURACY_WORKSPACE_BROWSER_E2E.md",
        "release/V36_9_PROGRAM_CLOSURE_CONTRACT.json",
        "release/V36_9_PROGRAM_CLOSURE.md",
        "release/V36_RELEASE_EVIDENCE.md",
        "src/socmint/source_registry_v36_1.py",
        "src/socmint/canonical_observation_v36_2.py",
        "src/socmint/entity_candidate_resolution_v36_3.py",
        "src/socmint/source_independence_v36_4.py",
        "src/socmint/claim_verification_v36_5.py",
        "src/socmint/relationship_timeline_v36_6.py",
        "src/socmint/dossier_synthesis_v36_7.py",
        "src/socmint/entity_accuracy_workspace_v36_8.py",
        "scripts/run_v36_8_entity_accuracy_workspace_browser_e2e.py",
    )
    for relative in required:
        assert (ROOT / relative).exists(), relative


def test_v36_9_release_evidence_states_the_read_only_safety_result():
    closure = CLOSURE.read_text(encoding="utf-8")
    evidence = EVIDENCE.read_text(encoding="utf-8")
    assert "v36 is closed" in closure
    assert "no v36 runtime or schema work remains" in closure
    assert "CI **4310**" in closure
    assert "combined v32 through v36 browser E2E **172**" in closure
    assert "6aa600ea0623a1af52faad3955a521c22bdf9a09" in evidence
    assert "94bb889e3cda2e378a57190eac0d1a50714eb800" in evidence
    assert "absence of forms" in evidence
    assert "support ranking from truth" in evidence


def test_v36_9_is_documentation_and_test_only():
    assert not list((ROOT / "src/socmint").glob("*v36_9*.py"))
    assert not list((ROOT / "src/socmint/templates").glob("*v36_9*.html"))
    assert not list((ROOT / "migrations").glob("*v36_9*"))
