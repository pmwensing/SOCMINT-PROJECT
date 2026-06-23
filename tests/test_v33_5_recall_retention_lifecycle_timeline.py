from src.socmint import recall_retention_lifecycle_timeline_v33_5 as timeline


def test_v33_5_builds_deterministic_lifecycle_timeline(monkeypatch):
    monkeypatch.setattr(
        timeline,
        "build_case_governance_snapshot",
        lambda case_id: {
            "status": "attention_required",
            "case_id": case_id,
            "snapshot_sha256": "snapshot-sha",
            "blockers": [{"key": "retention_decision_required", "stage": "retention"}],
        },
    )
    monkeypatch.setattr(
        timeline,
        "build_case_action_queue",
        lambda case_id: {
            "queue_summary_sha256": "queue-sha",
            "next_action": "record_retention_decision",
            "action_queue": [{"action": "record_retention_decision", "stage": "retention"}],
        },
    )
    monkeypatch.setattr(
        timeline,
        "recall_decision_history",
        lambda: [{
            "case_id": "case-1",
            "recall_decision_id": "recall-1",
            "dissemination_package_id": "package-1",
            "recall_state": "recalled",
            "recorded_at": "2026-01-01T00:00:00",
        }],
    )
    monkeypatch.setattr(
        timeline,
        "retention_decision_history",
        lambda: [{
            "case_id": "case-1",
            "retention_decision_id": "retention-1",
            "retention_state": "legal_hold",
            "recorded_at": "2026-01-02T00:00:00",
        }],
    )
    monkeypatch.setattr(timeline, "current_recall_state", lambda package_id: "recalled")
    monkeypatch.setattr(timeline, "current_retention_state", lambda case_id: "legal_hold")
    monkeypatch.setattr(timeline, "lifecycle_snapshot", lambda case_id: {"case_id": case_id})

    result = timeline.build_case_recall_retention_lifecycle_timeline("case-1")

    assert result["status"] == "attention_required"
    assert result["current_recall_states"]["package-1"] == "recalled"
    assert result["current_retention_state"] == "legal_hold"
    assert [item["stage"] for item in result["timeline"]] == ["recall", "retention"]
    assert result["timeline_sha256"]
    assert result["historical_evidence_preserved"] is True
