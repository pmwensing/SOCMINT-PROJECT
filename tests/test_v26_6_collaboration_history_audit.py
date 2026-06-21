import datetime as dt

from src.socmint import collaboration_history_audit_v26_6 as history


def test_v26_6_orders_history_and_builds_current_state(monkeypatch):
    monkeypatch.setattr(
        history,
        "_persisted_events",
        lambda allowed: [
            {
                "history_event_id": "e2",
                "event_type": "request_created",
                "occurred_at": "2026-06-16T10:00:00+00:00",
                "actor": "paul",
                "affected_user": "alice",
                "case_id": "case-a",
                "source_action": "case_collaboration_request_created",
                "source_record_id": 2,
                "source_binding_sha256": "b" * 64,
            },
            {
                "history_event_id": "e1",
                "event_type": "team_assignment",
                "occurred_at": "2026-06-16T09:00:00+00:00",
                "actor": "supervisor",
                "affected_user": "paul",
                "case_id": "case-a",
                "source_action": "case_team_role_assignment",
                "source_record_id": 1,
                "source_binding_sha256": "a" * 64,
            },
        ],
    )
    monkeypatch.setattr(
        history,
        "build_collaboration_workspace",
        lambda *a, **k: {
            "participating_cases": [{"case_id": "case-a"}],
        },
    )
    monkeypatch.setattr(
        history,
        "build_team_workload_collaboration_queue",
        lambda *a, **k: {
            "schema": "queue",
            "version": "v26.5.0",
            "status": "attention_required",
            "counts": {"overdue_items": 1},
            "queue_sha256": "q" * 64,
            "user_identity": "paul",
            "access_scope": {"allowed_case_ids": ["case-a"]},
            "awaiting_acknowledgement": [{"case_id": "case-a"}],
            "overdue_items": [{"case_id": "case-a"}],
            "supervisor_escalations": [],
        },
    )
    monkeypatch.setattr(
        history,
        "current_case_team",
        lambda case_id: [
            {
                "assignment_status": "active",
                "user_identity": "paul",
                "role": "case_owner",
                "case_team_assignment_id": "a1",
            }
        ],
    )
    monkeypatch.setattr(
        history,
        "build_requests_workspace",
        lambda case_id: {
            "pending_requests": [{"collaboration_request_id": "r1"}],
            "pending_handoffs": [],
        },
    )
    monkeypatch.setattr(
        history,
        "build_collaboration_response_workspace",
        lambda case_id: {
            "unresolved_responses": [
                {"target_id": "r1", "response_type": "acknowledgement"}
            ]
        },
    )

    result = history.build_collaboration_history_audit(
        "paul",
        allowed_case_ids={"case-a"},
        now=dt.datetime(2026, 6, 16, 12, 0, tzinfo=dt.UTC),
    )

    assert result["status"] == "attention_required"
    assert [item["history_event_id"] for item in result["history"][:2]] == ["e1", "e2"]
    assert result["event_type_counts"]["queue_checkpoint"] == 1
    assert result["current_collaboration_state"]["current_owner"] == "paul"
    assert result["current_collaboration_state"]["unresolved_actions"]["overdue"] == 1
    assert len(result["current_collaboration_state_sha256"]) == 64
    assert result["source_records_mutated"] is False
    assert result["history_record_created"] is False


def test_v26_6_empty_scope_is_ready(monkeypatch):
    monkeypatch.setattr(history, "_persisted_events", lambda allowed: [])
    monkeypatch.setattr(
        history,
        "build_collaboration_workspace",
        lambda *a, **k: {"participating_cases": []},
    )
    monkeypatch.setattr(
        history,
        "build_team_workload_collaboration_queue",
        lambda *a, **k: {
            "schema": "queue",
            "version": "v26.5.0",
            "status": "ready",
            "counts": {},
            "queue_sha256": "q" * 64,
            "user_identity": "paul",
            "access_scope": {},
            "awaiting_acknowledgement": [],
            "overdue_items": [],
            "supervisor_escalations": [],
        },
    )
    result = history.build_collaboration_history_audit(
        "paul",
        allowed_case_ids=set(),
        now=dt.datetime(2026, 6, 16, 12, 0, tzinfo=dt.UTC),
    )
    assert result["status"] == "ready"
    assert result["case_count"] == 0
    assert result["event_count"] == 1
