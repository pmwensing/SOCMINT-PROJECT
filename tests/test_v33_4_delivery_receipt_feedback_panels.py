from src.socmint import delivery_receipt_feedback_panels_v33_4 as panels


def _snapshot(case_id="case-1"):
    return {
        "status": "attention_required",
        "case_id": case_id,
        "snapshot_sha256": "snapshot-sha",
        "current": {
            "delivery_attempt": {
                "delivery_attempt_id": "attempt-2",
                "attempt_result": "failed",
                "endpoint_reference": "hidden",
            },
            "delivery_receipt": {
                "delivery_receipt_id": "receipt-2",
                "delivery_result": "failed",
                "acknowledgement_required": False,
            },
            "recipient_feedback": {
                "recipient_feedback_id": "feedback-2",
                "feedback_payload": {
                    "feedback_type": "error_report",
                    "severity": "high",
                },
            },
            "correction_intake": {
                "correction_intake_id": "correction-1",
                "recipient_feedback_id": "feedback-1",
                "correction_review": {"correction_action": "editorial_review"},
            },
        },
        "blockers": [{"key": "correction_review_required", "stage": "feedback"}],
    }


def _patch(monkeypatch):
    monkeypatch.setattr(panels, "build_case_governance_snapshot", _snapshot)
    monkeypatch.setattr(
        panels,
        "build_case_action_queue",
        lambda case_id: {
            "queue_summary_sha256": "queue-sha",
            "next_action": "record_correction_intake",
            "action_queue": [
                {
                    "action": "record_correction_intake",
                    "stage": "feedback",
                    "confirmation_required": True,
                }
            ],
        },
    )
    monkeypatch.setattr(
        panels,
        "delivery_attempt_history",
        lambda: [
            {"case_id": "case-1", "delivery_attempt_id": "attempt-1", "attempt_result": "accepted"},
            {"case_id": "case-1", "delivery_attempt_id": "attempt-2", "attempt_result": "failed"},
        ],
    )
    monkeypatch.setattr(
        panels,
        "delivery_receipt_history",
        lambda: [
            {
                "case_id": "case-1",
                "delivery_receipt_id": "receipt-1",
                "delivery_result": "delivered",
                "acknowledgement_required": True,
            },
            {"case_id": "case-1", "delivery_receipt_id": "receipt-2", "delivery_result": "failed"},
        ],
    )
    monkeypatch.setattr(
        panels,
        "recipient_feedback_history",
        lambda: [
            {
                "case_id": "case-1",
                "recipient_feedback_id": "feedback-1",
                "feedback_type": "acknowledgement",
                "correction_review_required": False,
            },
            {
                "case_id": "case-1",
                "recipient_feedback_id": "feedback-2",
                "feedback_payload": {"feedback_type": "error_report", "severity": "high"},
                "correction_review_required": True,
                "api-token": "hidden",
            },
        ],
    )
    monkeypatch.setattr(
        panels,
        "correction_intake_history",
        lambda: [
            {
                "case_id": "case-1",
                "correction_intake_id": "correction-1",
                "recipient_feedback_id": "feedback-1",
                "correction_state": "intake_recorded_pending_action",
                "correction_review": {"correction_action": "editorial_review"},
            }
        ],
    )


def test_v33_4_builds_current_state_panels(monkeypatch):
    _patch(monkeypatch)
    result = panels.build_case_delivery_receipt_feedback_panels("case-1")

    assert result["panel_order"] == ["delivery", "receipt", "feedback", "correction"]
    assert result["panels"]["delivery"]["state"]["current_result"] == "failed"
    assert result["panels"]["receipt"]["state"]["current_result"] == "failed"
    assert result["panels"]["receipt"]["state"]["acknowledgement_verified"] is True
    assert result["panels"]["feedback"]["state"]["unresolved_feedback_ids"] == ["feedback-2"]
    assert result["panels"]["feedback"]["state"]["resolved_feedback_ids"] == ["feedback-1"]
    assert result["status"] == "attention_required"
    assert result["panels_sha256"]


def test_v33_4_sanitizes_sensitive_fields(monkeypatch):
    _patch(monkeypatch)
    delivery = panels.build_case_delivery_receipt_feedback_panel("case-1", "delivery")
    feedback = panels.build_case_delivery_receipt_feedback_panel("case-1", "feedback")

    assert "endpoint_reference" not in delivery["current"]
    assert "api-token" not in feedback["history"][1]
    assert feedback["sensitive_values_rendered"] is False


def test_v33_4_blocks_invalid_panel(monkeypatch):
    _patch(monkeypatch)
    result = panels.build_case_delivery_receipt_feedback_panel("case-1", "unknown")
    assert result["status"] == "blocked"
    assert result["blockers"][0]["key"] == "invalid_panel"
