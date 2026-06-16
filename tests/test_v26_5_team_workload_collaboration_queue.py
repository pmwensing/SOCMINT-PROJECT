import datetime as dt

from src.socmint.team_workload_collaboration_queue_v26_5 import (
    build_team_workload_collaboration_queue,
)


def test_v26_5_aggregates_my_work_overdue_escalations_and_load():
    now = dt.datetime(2026, 6, 16, 20, 0, tzinfo=dt.UTC)
    workspace = {
        "participating_cases": [
            {"case_id": "case-a", "assigned_roles": ["reviewer"]},
            {"case_id": "case-b", "assigned_roles": ["supervisor"]},
        ],
        "pending_requests": [
            {
                "collaboration_request_id": "r1",
                "case_id": "case-a",
                "status": "requested",
                "requested_by": "paul",
                "requested_from": "alice",
                "due_at": "2026-06-16T18:00:00+00:00",
            }
        ],
        "pending_handoffs": [
            {
                "collaboration_handoff_id": "h1",
                "case_id": "case-b",
                "status": "accepted",
                "handoff_from": "bob",
                "handoff_to": "paul",
                "due_at": "2026-06-17T18:00:00+00:00",
            }
        ],
        "unread_updates": [{"case_id": "case-a", "collaboration_update_id": "u1"}],
    }
    workload = {
        "entries": [
            {
                "case_id": "case-a",
                "outstanding": True,
                "assigned_reviewer": "",
                "review_state": "unreviewed",
                "assignment_age_hours": 10.0,
                "decision_record_id": 12,
            }
        ]
    }
    teams = {
        "case-a": [
            {"assignment_status": "active", "user_identity": "alice", "role": "reviewer"},
            {"assignment_status": "active", "user_identity": "paul", "role": "lead_analyst"},
        ],
        "case-b": [
            {"assignment_status": "active", "user_identity": "bob", "role": "analyst"},
        ],
    }
    responses = {
        "case-a": {
            "unresolved_responses": [
                {
                    "target_type": "request",
                    "target_id": "r1",
                    "response_type": "escalation",
                    "responding_user": "supervisor",
                }
            ],
            "history": [],
        },
        "case-b": {"unresolved_responses": [], "history": []},
    }
    events = [
        {
            "case_id": "case-a",
            "action": "case_collaboration_note_created",
            "actor": "alice",
            "occurred_at": "2026-06-16T19:00:00+00:00",
            "record_id": 99,
        }
    ]

    result = build_team_workload_collaboration_queue(
        "paul",
        allowed_case_ids={"case-a", "case-b"},
        collaboration_workspace=workspace,
        workload=workload,
        team_by_case=teams,
        response_by_case=responses,
        collaboration_events=events,
        now=now,
    )

    assert result["status"] == "attention_required"
    assert result["counts"] == {
        "my_assigned_cases": 2,
        "pending_requests": 1,
        "awaiting_acknowledgement": 0,
        "delegated_by_me": 1,
        "pending_handoffs": 1,
        "overdue_items": 1,
        "unassigned_work": 1,
        "supervisor_escalations": 1,
        "recent_activity": 1,
        "users_with_load": 3,
        "workload_imbalance": 0,
    }
    assert result["overdue_items"][0]["overdue_hours"] == 2.0
    assert result["unassigned_work"][0]["links"]["reviewer_queue"] == "/case-intelligence-review/queue"
    assert result["supervisor_escalations"][0]["links"]["supervisor_queue"] == "/case-intelligence-review/supervisor-queue"
    loads = {item["user_identity"]: item for item in result["collaboration_load_by_user"]}
    assert loads["paul"]["total_collaboration_load"] == 3
    assert loads["alice"]["total_collaboration_load"] == 2
    assert len(result["queue_sha256"]) == 64
    assert result["read_only"] is True
    assert result["source_records_mutated"] is False
    assert result["collaboration_record_created"] is False


def test_v26_5_empty_queue_is_ready_and_deterministic():
    now = dt.datetime(2026, 6, 16, 20, 0, tzinfo=dt.UTC)
    kwargs = {
        "allowed_case_ids": set(),
        "collaboration_workspace": {
            "participating_cases": [],
            "pending_requests": [],
            "pending_handoffs": [],
            "unread_updates": [],
        },
        "workload": {"entries": []},
        "team_by_case": {},
        "response_by_case": {},
        "collaboration_events": [],
        "now": now,
    }
    first = build_team_workload_collaboration_queue("paul", **kwargs)
    second = build_team_workload_collaboration_queue("paul", **kwargs)
    assert first["status"] == "ready"
    assert first["counts"]["overdue_items"] == 0
    assert first["queue_sha256"] == second["queue_sha256"]
    assert first["generated_at"] == "2026-06-16T20:00:00+00:00"
