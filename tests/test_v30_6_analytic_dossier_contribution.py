from src.socmint import database
from src.socmint import analytic_dossier_contribution_v30_6 as contribution


def _claim():
    return {
        "claim_id": "claim-1",
        "claim_state": "proposed",
        "case_id": "case-1",
        "entity_id": "entity-1",
        "claim_event_sha256": "a" * 64,
    }


def _review(decision: str = "approved"):
    return {
        "human_review_id": "review-1",
        "human_review_sha256": "b" * 64,
        "decision": decision,
        "consequential_use_authorized": decision == "approved",
    }


def test_v30_6_approves_and_reassesses_without_dossier_mutation(monkeypatch, tmp_path):
    database.configure_database(f"sqlite:///{tmp_path / 'contributions.db'}")
    monkeypatch.setattr(contribution, "find_claim", lambda claim_id: _claim())
    monkeypatch.setattr(contribution, "latest_review", lambda claim_id: _review())

    approved = contribution.review_dossier_contribution(
        actor="reviewer",
        claim_id="claim-1",
        decision="approved",
        target_section="identity_findings",
        rationale="approved human review supports contribution",
        reason="authorize contribution eligibility",
        confirmed=True,
    )
    assert approved["status"] == "analytic_dossier_contribution_reviewed"
    assert approved["dossier_contribution_authorized"] is True
    assert approved["dossier_mutation_performed"] is False
    assert approved["is_reassessment"] is False

    held = contribution.review_dossier_contribution(
        actor="reviewer-2",
        claim_id="claim-1",
        decision="held",
        target_section="identity_findings",
        rationale="new context requires another review",
        reason="reassess contribution decision",
        confirmed=True,
    )
    assert held["status"] == "analytic_dossier_contribution_reviewed"
    assert held["is_reassessment"] is True
    assert held["supersedes_contribution_id"] == approved["dossier_contribution_id"]
    current = contribution.current_contribution_decisions()[0]
    assert current["decision"] == "held"
    assert len(current["contribution_history"]) == 2


def test_v30_6_blocks_approval_without_approved_human_review_and_invalid_withdrawal(monkeypatch, tmp_path):
    database.configure_database(f"sqlite:///{tmp_path / 'blocked.db'}")
    monkeypatch.setattr(contribution, "find_claim", lambda claim_id: _claim())
    monkeypatch.setattr(contribution, "latest_review", lambda claim_id: _review("held"))

    blocked = contribution.review_dossier_contribution(
        actor="reviewer",
        claim_id="claim-1",
        decision="approved",
        target_section="identity_findings",
        rationale="attempt approval",
        reason="review contribution",
        confirmed=True,
    )
    assert blocked["status"] == "blocked"
    assert blocked["blockers"][0]["key"] == "approved_human_review_required"

    withdrawal = contribution.review_dossier_contribution(
        actor="reviewer",
        claim_id="claim-1",
        decision="withdrawn",
        target_section="",
        rationale="attempt withdrawal without approval",
        reason="withdraw contribution",
        confirmed=True,
    )
    assert withdrawal["status"] == "blocked"
    assert withdrawal["blockers"][0]["key"] == "approved_contribution_required_for_withdrawal"
