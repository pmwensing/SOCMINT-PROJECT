from src.socmint import recipient_feedback_correction_intake_v32_5 as intake


RECEIPT = {
    "case_id": "case-1",
    "delivery_receipt_id": "receipt-1",
    "delivery_receipt_sha256": "receipt-sha-1",
    "delivery_attempt_id": "attempt-1",
    "dissemination_package_id": "package-1",
    "authorization_decision_id": "authorization-1",
    "recipient_id": "recipient-1",
    "delivery_channel": "secure_portal",
    "delivery_result": "delivered",
}


def test_v32_5_records_feedback_separately(monkeypatch):
    monkeypatch.setattr(intake, "find_delivery_receipt", lambda receipt_id: RECEIPT)
    monkeypatch.setattr(intake, "recipient_feedback_history", lambda: [])
    monkeypatch.setattr(
        intake,
        "_record",
        lambda **kwargs: {**kwargs["event"], "recorded_by": kwargs["actor"]},
    )

    result = intake.record_recipient_feedback(
        recorder="admin",
        delivery_receipt_id="receipt-1",
        feedback_type="error_report",
        severity="high",
        recipient_reference="recipient-1",
        summary="Incorrect date",
        detail="The date in the first finding appears incorrect.",
        confirmed=True,
    )

    assert result["status"] == "recipient_feedback_recorded"
    assert result["correction_review_required"] is True
    assert result["source_intelligence_mutated"] is False
    assert result["published_revision_mutated"] is False
    assert result["delivery_receipt_mutated"] is False


def test_v32_5_blocks_feedback_without_delivery(monkeypatch):
    receipt = {**RECEIPT, "delivery_result": "failed"}
    monkeypatch.setattr(intake, "find_delivery_receipt", lambda receipt_id: receipt)

    result = intake.record_recipient_feedback(
        recorder="admin",
        delivery_receipt_id="receipt-1",
        feedback_type="question",
        severity="low",
        recipient_reference="recipient-1",
        summary="Question",
        detail="Please clarify the finding.",
        confirmed=True,
    )

    assert result["status"] == "blocked"
    assert result["blockers"][0]["key"] == "delivered_receipt_required"
