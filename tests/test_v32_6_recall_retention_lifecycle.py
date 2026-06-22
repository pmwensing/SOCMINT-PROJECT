from src.socmint import recall_retention_lifecycle_v32_6 as lifecycle


CORRECTION = {
    "case_id": "case-1",
    "correction_intake_id": "correction-1",
    "correction_intake_sha256": "correction-sha-1",
    "recipient_feedback_id": "feedback-1",
    "dissemination_package_id": "package-1",
    "recall_review_required": True,
    "correction_review": {"correction_action": "recall_review"},
}

PACKAGE = {
    "case_id": "case-1",
    "dissemination_package_id": "package-1",
    "dissemination_package_sha256": "package-sha-1",
    "published_revision_id": "published-1",
    "published_revision_sha256": "published-sha-1",
}


def test_v32_6_records_append_only_recall_decision(monkeypatch):
    monkeypatch.setattr(
        lifecycle,
        "find_correction_intake",
        lambda correction_id: CORRECTION,
    )
    monkeypatch.setattr(
        lifecycle,
        "find_dissemination_package",
        lambda package_id: PACKAGE,
    )
    monkeypatch.setattr(lifecycle, "recall_decision_history", lambda: [])
    monkeypatch.setattr(
        lifecycle,
        "_record",
        lambda **kwargs: kwargs["event"],
    )

    result = lifecycle.record_recall_decision(
        reviewer="admin",
        correction_intake_id="correction-1",
        decision="initiate",
        reason="critical recipient error report",
        confirmed=True,
    )

    assert result["status"] == "recall_decision_recorded"
    assert result["recall_state"] == "recall_pending"
    assert result["future_delivery_blocked"] is True
    assert result["historical_evidence_preserved"] is True
    assert result["historical_evidence_deleted"] is False
    assert result["package_mutated"] is False
    assert result["external_transmission_performed"] is False


def test_v32_6_recall_requires_recall_review(monkeypatch):
    correction = {
        **CORRECTION,
        "recall_review_required": False,
        "correction_review": {"correction_action": "editorial_review"},
    }
    monkeypatch.setattr(
        lifecycle,
        "find_correction_intake",
        lambda correction_id: correction,
    )

    result = lifecycle.record_recall_decision(
        reviewer="admin",
        correction_intake_id="correction-1",
        decision="initiate",
        reason="review",
        confirmed=True,
    )

    assert result["status"] == "blocked"
    assert result["blockers"][0]["key"] == (
        "recall_review_correction_intake_required"
    )


def test_v32_6_records_policy_bound_retention(monkeypatch):
    monkeypatch.setattr(lifecycle, "retention_decision_history", lambda: [])
    monkeypatch.setattr(lifecycle, "recall_decision_history", lambda: [])
    monkeypatch.setattr(
        lifecycle,
        "_record",
        lambda **kwargs: kwargs["event"],
    )

    result = lifecycle.record_retention_decision(
        reviewer="admin",
        case_id="case-1",
        disposition="legal_hold",
        policy_id="policy-legal-7y",
        reason="active legal preservation requirement",
        confirmed=True,
    )

    assert result["status"] == "retention_decision_recorded"
    assert result["retention_state"] == "legal_hold"
    assert result["policy_bound"] is True
    assert result["legal_hold_active"] is True
    assert result["destructive_action_performed"] is False
    assert result["historical_evidence_deleted"] is False


def test_v32_6_lifecycle_history_is_case_scoped(monkeypatch):
    monkeypatch.setattr(
        lifecycle,
        "audience_contract_history",
        lambda: [
            {
                "case_id": "case-1",
                "audience_contract_id": "audience-1",
                "recorded_at": "2026-06-22T10:00:00",
            },
            {
                "case_id": "case-2",
                "audience_contract_id": "audience-2",
                "recorded_at": "2026-06-22T10:00:00",
            },
        ],
    )
    monkeypatch.setattr(lifecycle, "dissemination_package_history", lambda: [])
    monkeypatch.setattr(lifecycle, "authorization_decision_history", lambda: [])
    monkeypatch.setattr(lifecycle, "delivery_attempt_history", lambda: [])
    monkeypatch.setattr(lifecycle, "delivery_receipt_history", lambda: [])
    monkeypatch.setattr(lifecycle, "recipient_feedback_history", lambda: [])
    monkeypatch.setattr(lifecycle, "correction_intake_history", lambda: [])
    monkeypatch.setattr(lifecycle, "recall_decision_history", lambda: [])
    monkeypatch.setattr(lifecycle, "retention_decision_history", lambda: [])

    history = lifecycle.lifecycle_history("case-1")

    assert len(history) == 1
    assert history[0]["case_id"] == "case-1"
    assert history[0]["lifecycle_stage"] == "audience_contract"
