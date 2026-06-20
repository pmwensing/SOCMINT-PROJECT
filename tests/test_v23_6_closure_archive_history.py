from src.socmint import case_closure_history_v23_6 as service


def test_v23_6_builds_ordered_complete_history(monkeypatch):
    monkeypatch.setattr(
        service,
        "_events",
        lambda case_id: [
            {
                "timeline_id": 1,
                "event_type": "readiness_review",
                "action": "case_closure_readiness_review",
                "actor": "reviewer",
                "occurred_at": "2026-06-14T20:00:00",
                "details": {"decision": "ready", "review_id": "review-1"},
            },
            {
                "timeline_id": 2,
                "event_type": "closure_decision",
                "action": "case_supervisor_closure_decision",
                "actor": "supervisor",
                "occurred_at": "2026-06-14T20:10:00",
                "details": {"decision": "close", "closure_decision_id": "decision-1"},
            },
            {
                "timeline_id": 3,
                "event_type": "retention_assignment",
                "action": "case_retention_policy_assignment",
                "actor": "records",
                "occurred_at": "2026-06-14T20:20:00",
                "details": {
                    "retention_assignment_id": "retention-1",
                    "disposition": {
                        "disposition": "retain_until_expiration",
                        "archive_class": "standard",
                        "retention_years": 7,
                        "retention_expires_at": "2033-06-14T20:10:00",
                        "legal_hold": False,
                    },
                },
            },
            {
                "timeline_id": 4,
                "event_type": "archive_generation",
                "action": "case_archive_package_generated",
                "actor": "records",
                "occurred_at": "2026-06-14T20:30:00",
                "details": {"archive_package_id": "archive-1"},
            },
        ],
    )

    result = service.build_case_closure_history("case-alpha")

    assert result["status"] == "complete"
    assert result["event_count"] == 4
    assert result["current_closure_state"] == "closed"
    assert result["current_archive_state"] == "generated"
    assert result["retention_disposition"]["disposition"] == "retain_until_expiration"
    assert result["reopen_status"] == "none"
    assert result["unresolved_actions"] == []
    assert result["next_action"] == "product_review_checkpoint"
    assert result["source_records_mutated"] is False
    assert result["history_record_created"] is False


def test_v23_6_tracks_reopen_and_unresolved_actions(monkeypatch):
    monkeypatch.setattr(
        service,
        "_events",
        lambda case_id: [
            {
                "timeline_id": 1,
                "event_type": "readiness_review",
                "action": "case_closure_readiness_review",
                "actor": "reviewer",
                "occurred_at": "2026-06-14T20:00:00",
                "details": {"decision": "ready"},
            },
            {
                "timeline_id": 2,
                "event_type": "closure_decision",
                "action": "case_supervisor_closure_decision",
                "actor": "supervisor",
                "occurred_at": "2026-06-14T20:10:00",
                "details": {"decision": "close"},
            },
            {
                "timeline_id": 3,
                "event_type": "reopen_request",
                "action": "case_reopen_request",
                "actor": "analyst",
                "occurred_at": "2026-06-14T20:40:00",
                "details": {"reopen_request_id": "request-1"},
            },
        ],
    )

    pending = service.build_case_closure_history("case-alpha")
    assert pending["status"] == "attention_required"
    assert pending["current_closure_state"] == "closed"
    assert pending["current_archive_state"] == "not_generated"
    assert pending["reopen_status"] == "pending_authorization"
    keys = {item["key"] for item in pending["unresolved_actions"]}
    assert "retention_assignment_required" in keys
    assert "reopen_authorization_required" in keys

    monkeypatch.setattr(
        service,
        "_events",
        lambda case_id: [
            *pending["timeline"],
            {
                "timeline_id": 4,
                "event_type": "reopen_authorization",
                "action": "case_reopen_authorization",
                "actor": "supervisor",
                "occurred_at": "2026-06-14T20:50:00",
                "details": {"decision": "authorize", "case_reopen_authorized": True},
            },
        ],
    )
    reopened = service.build_case_closure_history("case-alpha")
    assert reopened["current_closure_state"] == "reopened"
    assert reopened["reopen_status"] == "authorized"
