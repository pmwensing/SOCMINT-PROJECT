from src.socmint import database
from src.socmint import analytic_confidence_v30_4 as confidence


def _claim():
    return {
        "claim_id": "claim-1",
        "claim_state": "proposed",
        "case_id": "case-1",
        "entity_id": "entity-1",
        "claim_event_sha256": "a" * 64,
    }


def _linkage():
    return {
        "linkage_id": "linkage-1",
        "linkage_sha256": "b" * 64,
        "source_manifest": {
            "artifact_bindings": [
                {"artifact_id": "artifact-1"},
                {"artifact_id": "artifact-2"},
            ],
            "observation_bindings": [
                {"observation_id": "observation-1"},
                {"observation_id": "observation-2"},
            ],
        },
    }


def test_v30_4_records_explainable_bounded_confidence(monkeypatch, tmp_path):
    database.configure_database(f"sqlite:///{tmp_path / 'confidence.db'}")
    monkeypatch.setattr(confidence, "find_claim", lambda claim_id: _claim())
    monkeypatch.setattr(confidence, "claim_linkages", lambda claim_id: [_linkage()])
    monkeypatch.setattr(confidence, "current_conflicts", lambda: [])

    result = confidence.assess_confidence(
        actor="analyst",
        claim_id="claim-1",
        methodology="deterministic source and conflict weighting",
        limitations=["source recency not independently verified"],
        reason="record explainable confidence",
        confirmed=True,
    )

    assert result["status"] == "analytic_confidence_assessed"
    assert 0 <= result["confidence_score"] <= 79
    assert result["confidence_band"] in confidence.BANDS
    assert result["truth_assigned"] is False
    assert result["high_confidence_assigned"] is False
    assert result["human_review_complete"] is False
    assert result["explanation"]["score_cap"] == 79
    assert len(confidence.confidence_assessments("claim-1")) == 1


def test_v30_4_penalizes_unresolved_conflicts_and_blocks_unlinked_claim(monkeypatch, tmp_path):
    database.configure_database(f"sqlite:///{tmp_path / 'blocked.db'}")
    monkeypatch.setattr(confidence, "find_claim", lambda claim_id: _claim())
    monkeypatch.setattr(confidence, "claim_linkages", lambda claim_id: [])
    monkeypatch.setattr(confidence, "current_conflicts", lambda: [])

    blocked = confidence.assess_confidence(
        actor="analyst",
        claim_id="claim-1",
        methodology="deterministic",
        limitations=[],
        reason="attempt without linkage",
        confirmed=True,
    )
    assert blocked["status"] == "blocked"
    assert blocked["blockers"][0]["key"] == "claim_source_linkage_required"

    monkeypatch.setattr(confidence, "claim_linkages", lambda claim_id: [_linkage()])
    monkeypatch.setattr(confidence, "current_conflicts", lambda: [{
        "conflict_id": "conflict-1",
        "claim_a_id": "claim-1",
        "claim_b_id": "claim-2",
        "resolution": "unresolved",
        "conflict_event_sha256": "c" * 64,
    }])
    result = confidence.assess_confidence(
        actor="analyst",
        claim_id="claim-1",
        methodology="deterministic",
        limitations=[],
        reason="include unresolved conflict",
        confirmed=True,
    )
    assert "conflict-1" in result["explanation"]["unresolved_conflict_ids"]
    penalty = next(item for item in result["explanation"]["components"] if item["key"] == "unresolved_conflict_penalty")
    assert penalty["points"] < 0
