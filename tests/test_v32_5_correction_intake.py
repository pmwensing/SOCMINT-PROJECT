from src.socmint import recipient_feedback_correction_intake_v32_5 as intake


def test_v32_5_records_new_revision_review(monkeypatch):
    feedback = {
        "case_id": "case-1",
        "recipient_feedback_id": "feedback-1",
        "recipient_feedback_sha256": "feedback-sha-1",
        "delivery_receipt_id": "receipt-1",
        "delivery_attempt_id": "attempt-1",
        "dissemination_package_id": "package-1",
        "authorization_decision_id": "authorization-1",
    }
    monkeypatch.setattr(intake, "find_recipient_feedback", lambda feedback_id: feedback)
    monkeypatch.setattr(intake, "correction_intake_history", lambda: [])
    monkeypatch.setattr(
        intake,
        "_record",
        lambda **kwargs: kwargs["event"],
    )

    result = intake.record_correction_intake(
        reviewer="admin",
        recipient_feedback_id="feedback-1",
        correction_action="new_revision_review",
        reason="substantive correction required",
        confirmed=True,
        affected_section_ids=["key_findings"],
        proposed_resolution="Create a new reviewed revision.",
    )

    assert result["status"] == "correction_intake_recorded"
    assert result["new_revision_required"] is True
    assert result["published_revision_mutated"] is False
    assert result["prior_feedback_mutated"] is False
    assert result["next_action"] == "assemble_new_draft_revision"


def test_v32_5_requires_correction_confirmation():
    result = intake.record_correction_intake(
        reviewer="admin",
        recipient_feedback_id="feedback-1",
        correction_action="editorial_review",
        reason="review requested",
        confirmed=False,
        proposed_resolution="Review wording.",
    )

    assert result["status"] == "blocked"
    assert result["blockers"][0]["key"] == (
        "explicit_correction_intake_confirmation_required"
    )
