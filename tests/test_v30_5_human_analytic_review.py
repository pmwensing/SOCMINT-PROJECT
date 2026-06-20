from src.socmint import database
from src.socmint import human_analytic_review_v30_5 as review


def _claim():
    return {
        "claim_id": "claim-1",
        "claim_state": "proposed",
        "case_id": "case-1",
        "entity_id": "entity-1",
        "claim_event_sha256": "a" * 64,
    }


def _confidence(band: str = "substantial"):
    return {
        "confidence_assessment_id": "confidence-1",
        "confidence_assessment_sha256": "b" * 64,
        "confidence_band": band,
        "confidence_score": 70,
    }


def _linkage():
    return {"linkage_id": "linkage-1", "linkage_sha256": "c" * 64}


def test_v30_5_records_approval_and_preserves_reassessment_history(
    monkeypatch, tmp_path
):
    database.configure_database(f"sqlite:///{tmp_path / 'reviews.db'}")
    monkeypatch.setattr(review, "find_claim", lambda claim_id: _claim())
    monkeypatch.setattr(review, "latest_confidence", lambda claim_id: _confidence())
    monkeypatch.setattr(review, "claim_linkages", lambda claim_id: [_linkage()])
    monkeypatch.setattr(review, "current_conflicts", lambda: [])

    approved = review.record_human_review(
        actor="reviewer",
        claim_id="claim-1",
        decision="approved",
        rationale="sources and confidence support consequential use",
        findings=["source bindings verified"],
        reason="complete human review",
        confirmed=True,
    )
    assert approved["status"] == "human_analytic_review_recorded"
    assert approved["human_review_complete"] is True
    assert approved["consequential_use_authorized"] is True
    assert approved["dossier_contribution_authorized"] is False
    assert approved["is_reassessment"] is False

    held = review.record_human_review(
        actor="reviewer-2",
        claim_id="claim-1",
        decision="held",
        rationale="new context requires reassessment",
        findings=["additional source pending"],
        reason="reassess prior decision",
        confirmed=True,
    )
    assert held["status"] == "human_analytic_review_recorded"
    assert held["is_reassessment"] is True
    assert held["supersedes_review_id"] == approved["human_review_id"]
    current = review.current_review_decisions()[0]
    assert current["decision"] == "held"
    assert len(current["review_history"]) == 2


def test_v30_5_blocks_approval_without_substantial_confidence_or_with_conflict(
    monkeypatch, tmp_path
):
    database.configure_database(f"sqlite:///{tmp_path / 'blocked.db'}")
    monkeypatch.setattr(review, "find_claim", lambda claim_id: _claim())
    monkeypatch.setattr(review, "claim_linkages", lambda claim_id: [_linkage()])
    monkeypatch.setattr(
        review, "latest_confidence", lambda claim_id: _confidence("moderate")
    )
    monkeypatch.setattr(review, "current_conflicts", lambda: [])

    moderate = review.record_human_review(
        actor="reviewer",
        claim_id="claim-1",
        decision="approved",
        rationale="attempt approval",
        findings=[],
        reason="review",
        confirmed=True,
    )
    assert moderate["status"] == "blocked"
    assert (
        moderate["blockers"][0]["key"] == "substantial_confidence_required_for_approval"
    )

    monkeypatch.setattr(review, "latest_confidence", lambda claim_id: _confidence())
    monkeypatch.setattr(
        review,
        "current_conflicts",
        lambda: [
            {
                "conflict_id": "conflict-1",
                "claim_a_id": "claim-1",
                "claim_b_id": "claim-2",
                "resolution": "unresolved",
                "conflict_event_sha256": "d" * 64,
            }
        ],
    )
    unresolved = review.record_human_review(
        actor="reviewer",
        claim_id="claim-1",
        decision="approved",
        rationale="attempt approval",
        findings=[],
        reason="review",
        confirmed=True,
    )
    assert unresolved["status"] == "blocked"
    assert (
        unresolved["blockers"][0]["key"]
        == "unresolved_analytic_conflict_blocks_approval"
    )
