import datetime as dt

from src.socmint import portfolio_workload_monitoring_v24_2 as service


def test_v24_2_aggregates_assignments_unassigned_and_review_states(monkeypatch):
    monkeypatch.setattr(service, "build_persistent_decision_supervisor_queue", lambda now=None: {
        "counts": {"unreviewed": 2, "needs_follow_up": 1, "reviewed": 1, "accepted": 0},
        "entries": [
            {
                "decision_record_id": 1,
                "case_id": "case-a",
                "decision": "accept",
                "review_state": "unreviewed",
                "assigned_reviewer": "alice",
                "assigned_at": "2026-06-15T10:00:00+00:00",
                "age_hours": 8.0,
                "case_workspace_href": "/case-intelligence-review/case-a",
            },
            {
                "decision_record_id": 2,
                "case_id": "case-b",
                "decision": "follow_up",
                "review_state": "needs_follow_up",
                "assigned_reviewer": "alice",
                "assigned_at": "2026-06-15T11:00:00+00:00",
                "age_hours": 7.0,
                "case_workspace_href": "/case-intelligence-review/case-b",
            },
            {
                "decision_record_id": 3,
                "case_id": "case-c",
                "decision": "accept",
                "review_state": "unreviewed",
                "assigned_reviewer": None,
                "assigned_at": None,
                "age_hours": 6.0,
                "case_workspace_href": "/case-intelligence-review/case-c",
            },
            {
                "decision_record_id": 4,
                "case_id": "case-d",
                "decision": "accept",
                "review_state": "reviewed",
                "assigned_reviewer": "bob",
                "assigned_at": "2026-06-15T12:00:00+00:00",
                "age_hours": 5.0,
                "case_workspace_href": "/case-intelligence-review/case-d",
            },
        ],
    })

    result = service.build_workload_assignment_monitoring(
        now=dt.datetime(2026, 6, 15, 14, 0, tzinfo=dt.UTC)
    )
    by_reviewer = {item["reviewer"]: item for item in result["reviewers"]}

    assert result["status"] == "attention_required"
    assert result["counts"] == {
        "total_decisions": 4,
        "active_workload": 3,
        "assigned_active": 2,
        "unassigned_active": 1,
        "reviewer_count": 2,
    }
    assert result["unassigned_work"][0]["case_id"] == "case-c"
    assert by_reviewer["alice"]["active_workload"] == 2
    assert by_reviewer["alice"]["oldest_assignment_age_hours"] == 4.0
    assert by_reviewer["alice"]["unreviewed"] == 1
    assert by_reviewer["alice"]["needs_follow_up"] == 1
    assert by_reviewer["bob"]["active_workload"] == 0
    assert result["workload_balance"]["workload_spread"] == 2
    assert result["workload_balance"]["imbalanced"] is True
    assert by_reviewer["alice"]["workload_imbalanced"] is True
    assert result["next_action"] == "assign_unassigned_work"
    assert result["source_assignments_mutated"] is False
    assert result["workload_record_created"] is False


def test_v24_2_reports_balanced_empty_workload(monkeypatch):
    monkeypatch.setattr(service, "build_persistent_decision_supervisor_queue", lambda now=None: {
        "counts": {},
        "entries": [],
    })
    result = service.build_workload_assignment_monitoring(
        now=dt.datetime(2026, 6, 15, 14, 0, tzinfo=dt.UTC)
    )
    assert result["status"] == "balanced"
    assert result["counts"]["active_workload"] == 0
    assert result["reviewers"] == []
    assert result["unassigned_work"] == []
    assert result["workload_balance"]["imbalanced"] is False
    assert result["next_action"] == "monitor_reviewer_workload"
