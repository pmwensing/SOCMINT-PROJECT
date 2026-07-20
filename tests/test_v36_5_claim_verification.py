from __future__ import annotations

from src.socmint import claim_verification_v36_5 as verification
from src.socmint import database


def _claim(claim_id: str, value: str = "Employer A"):
    return {
        "claim_id": claim_id,
        "claim_state": "proposed",
        "case_id": "case-a",
        "entity_id": "entity-a",
        "claim_type": "current_employer",
        "normalized_value": value,
        "claim_event_sha256": claim_id.ljust(64, "a")[:64],
    }


def _source(source_id: str, score: float = 90.0, directness: int = 90):
    return {
        "source_id": source_id,
        "case_id": "case-a",
        "source_event_sha256": source_id.ljust(64, "b")[:64],
        "capture_sha256": source_id.ljust(64, "c")[:64],
        "capture_integrity_verified": True,
        "source_reliability_profile": [
            {
                "claim_type": "current_employer",
                "reliability_score": score,
                "components": {"directness": directness},
                "source_reliability_assessment_id": f"profile-{source_id}",
            }
        ],
    }


def _configure(monkeypatch, tmp_path, claims=None, conflicts=None):
    database.configure_database(f"sqlite:///{tmp_path / 'verification.db'}")
    claims = claims or {"claim-1": _claim("claim-1")}
    sources = {
        "source-a": _source("source-a"),
        "source-b": _source("source-b"),
    }
    monkeypatch.setattr(
        verification,
        "find_claim",
        lambda claim_id: claims.get(claim_id),
    )
    monkeypatch.setattr(
        verification,
        "find_source",
        lambda source_id: sources.get(source_id),
    )
    monkeypatch.setattr(
        verification,
        "claim_linkages",
        lambda claim_id: [
            {
                "linkage_id": f"link-{claim_id}",
                "linkage_sha256": "d" * 64,
                "source_manifest": {
                    "artifact_bindings": [{"artifact_id": "artifact-1"}],
                    "observation_bindings": [{"observation_id": "obs-1"}],
                },
            }
        ],
    )
    monkeypatch.setattr(
        verification,
        "groups_for_sources",
        lambda source_ids: [
            {
                "independence_group_id": "group-1",
                "source_ids": sorted(source_ids),
                "relationship": "independent",
                "independence_score": 100,
                "source_independence_assessment_sha256": "e" * 64,
            }
        ],
    )
    monkeypatch.setattr(
        verification,
        "current_conflicts",
        lambda: conflicts or [],
    )
    monkeypatch.setattr(verification, "find_candidate", lambda candidate_id: None)


def _assess(claim_id="claim-1", **overrides):
    values = {
        "actor": "admin",
        "claim_id": claim_id,
        "source_ids": ["source-a", "source-b"],
        "identity_context": {
            "basis": "direct_verified_control",
            "reason": "Direct verified control links the subject to the claim context.",
        },
        "temporal_relevance_score": 90,
        "temporal_reason": "Both sources were current during the assessed period.",
        "limitations": [],
        "methodology": "Dimensional v36.5 source-grounded assessment.",
        "reason": "Assess support before human review.",
        "confirmed": True,
    }
    values.update(overrides)
    return verification.assess_claim_verification(**values)


def test_v36_5_produces_dimensional_substantial_assessment(monkeypatch, tmp_path):
    _configure(monkeypatch, tmp_path)
    result = _assess()
    assert result["status"] == "claim_verification_assessed"
    assert result["support_score"] == 79
    assert result["confidence_band"] == "substantial"
    assert result["dimensions"] == {
        "identity_score": 100,
        "source_score": 90.0,
        "directness_score": 90.0,
        "capture_integrity_score": 100.0,
        "temporal_relevance_score": 90,
        "independence_score": 100,
        "linkage_score": 100,
    }
    assert result["score_cap"] == 79
    assert result["truth_assigned"] is False
    assert result["human_review_complete"] is False
    assert result["dossier_eligible"] is False
    assert result["ranking"]["most_likely_supported"] is True


def test_v36_5_unresolved_conflicts_and_limitations_reduce_support(
    monkeypatch,
    tmp_path,
):
    _configure(
        monkeypatch,
        tmp_path,
        conflicts=[
            {
                "conflict_id": "conflict-1",
                "claim_a_id": "claim-1",
                "claim_b_id": "claim-2",
                "resolution": "unresolved",
                "conflict_event_sha256": "f" * 64,
            }
        ],
    )
    result = _assess(limitations=["One source may be stale."])
    assert result["conflict_penalty"] == 15
    assert result["limitation_penalty"] == 5
    assert result["support_score"] == 74
    assert result["unresolved_conflict_ids"] == ["conflict-1"]


def test_v36_5_ranks_competing_claims_and_detects_top_tie(monkeypatch, tmp_path):
    claims = {
        "claim-1": _claim("claim-1", "Employer A"),
        "claim-2": _claim("claim-2", "Employer B"),
    }
    _configure(monkeypatch, tmp_path, claims=claims)
    first = _assess("claim-1", temporal_relevance_score=90)
    second = _assess("claim-2", temporal_relevance_score=50)
    current_first = verification.find_verification("claim-1")
    current_second = verification.find_verification("claim-2")
    assert first["alternative_group_id"] == second["alternative_group_id"]
    assert current_first["ranking"]["position"] == 1
    assert current_first["ranking"]["most_likely_supported"] is True
    assert current_second["ranking"]["position"] == 2

    database.configure_database(f"sqlite:///{tmp_path / 'tie.db'}")
    tied_first = _assess("claim-1", temporal_relevance_score=80)
    tied_second = _assess("claim-2", temporal_relevance_score=80)
    assert tied_first["status"] == "claim_verification_assessed"
    assert tied_second["status"] == "claim_verification_assessed"
    assert verification.find_verification("claim-1")["ranking"]["tie_at_top"] is True
    assert verification.find_verification("claim-1")["ranking"][
        "most_likely_supported"
    ] is False


def test_v36_5_single_or_unassessed_sources_do_not_claim_independence(
    monkeypatch,
    tmp_path,
):
    _configure(monkeypatch, tmp_path)
    monkeypatch.setattr(verification, "groups_for_sources", lambda source_ids: [])
    result = _assess(source_ids=["source-a", "source-b"])
    assert result["independence_context"]["score"] == 0
    assert result["independence_context"]["reason"] == (
        "source_set_independence_not_assessed"
    )


def test_v36_5_requires_claim_type_source_profiles(monkeypatch, tmp_path):
    _configure(monkeypatch, tmp_path)
    monkeypatch.setattr(
        verification,
        "find_source",
        lambda source_id: {
            **_source(source_id),
            "source_reliability_profile": [],
        },
    )
    result = _assess()
    assert result["source_context"]["source_score"] == 0.0
    assert result["source_context"]["missing_claim_type_profiles"] == [
        "source-a",
        "source-b",
    ]


def test_v36_5_reviewed_candidate_requires_merge_recommendation(
    monkeypatch,
    tmp_path,
):
    _configure(monkeypatch, tmp_path)
    monkeypatch.setattr(
        verification,
        "find_candidate",
        lambda candidate_id: {
            "candidate_id": candidate_id,
            "case_id": "case-a",
            "scoring": {"score": 75},
            "current_decision": {"decision": "keep_separate"},
        },
    )
    result = _assess(
        identity_context={
            "basis": "reviewed_candidate",
            "candidate_id": "candidate-1",
            "reason": "Use reviewed candidate.",
        }
    )
    assert result["blockers"] == [
        {"key": "merge_recommended_entity_candidate_required"}
    ]
