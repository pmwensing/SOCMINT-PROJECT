import datetime as dt

from src.socmint import portfolio_operational_metrics_v24_5 as service


def test_v24_5_calculates_volume_rates_durations_and_trends(monkeypatch):
    now = dt.datetime(2026, 6, 15, 12, 0, tzinfo=dt.UTC)
    monkeypatch.setenv("SOCMINT_PORTFOLIO_TREND_WINDOWS", "7,30")
    monkeypatch.setattr(service, "build_portfolio_operations_dashboard", lambda: {
        "counts": {"active": 1, "blocked": 1, "delivered": 1, "closed": 1, "archived": 1, "reopened": 1},
        "cases": [
            {"case_id": "case-active", "stage": "active"},
            {"case_id": "case-delivered", "stage": "delivered"},
            {"case_id": "case-closed", "stage": "closed"},
            {"case_id": "case-archived", "stage": "archived"},
            {"case_id": "case-reopened", "stage": "reopened"},
        ],
    })
    monkeypatch.setattr(service, "build_case_status_stage_overview", lambda now=None: {
        "cases": [
            {"case_id": "case-active", "current_stage": "active"},
            {"case_id": "case-delivered", "current_stage": "delivered"},
            {"case_id": "case-closed", "current_stage": "closed"},
            {"case_id": "case-archived", "current_stage": "archived"},
            {"case_id": "case-reopened", "current_stage": "reopened"},
        ]
    })
    monkeypatch.setattr(service, "build_workload_assignment_monitoring", lambda now=None: {
        "reviewers": [
            {"reviewer": "alice", "reviewed": 3, "accepted": 1, "active_workload": 2, "total_assigned": 8, "average_assignment_age_hours": 10.0},
            {"reviewer": "bob", "reviewed": 1, "accepted": 0, "active_workload": 1, "total_assigned": 4, "average_assignment_age_hours": 5.0},
        ]
    })
    monkeypatch.setattr(service, "build_blocked_overdue_case_queue", lambda: {
        "queue": [
            {"case_id": "case-active", "stage_overdue": True, "assignment_overdue": False}
        ]
    })
    monkeypatch.setattr(service, "_case_events", lambda: {
        "case-closed": [
            {"record_id": 1, "action": "case_closure_readiness_review", "occurred_at": "2026-06-10T08:00:00+00:00", "details": {}},
            {"record_id": 2, "action": "case_supervisor_closure_decision", "occurred_at": "2026-06-10T12:00:00+00:00", "details": {"decision": "close"}},
        ],
        "case-archived": [
            {"record_id": 3, "action": "case_supervisor_closure_decision", "occurred_at": "2026-06-11T08:00:00+00:00", "details": {"decision": "close"}},
            {"record_id": 4, "action": "case_retention_policy_assignment", "occurred_at": "2026-06-11T10:00:00+00:00", "details": {}},
            {"record_id": 5, "action": "case_archive_package_generated", "occurred_at": "2026-06-11T14:00:00+00:00", "details": {}},
        ],
        "case-reopened": [
            {"record_id": 6, "action": "case_archive_package_generated", "occurred_at": "2026-06-12T08:00:00+00:00", "details": {}},
            {"record_id": 7, "action": "case_reopen_authorization", "occurred_at": "2026-06-12T12:00:00+00:00", "details": {"decision": "authorize"}},
        ],
    })

    result = service.build_operational_metrics(now=now)

    assert result["case_volume"] == {
        "total_cases": 5,
        "active_cases": 1,
        "completed_cases": 4,
        "blocked_cases": 1,
        "overdue_cases": 1,
    }
    assert result["completion_counts"] == {
        "delivered": 1,
        "closed": 3,
        "archived": 2,
        "reopened": 1,
    }
    assert result["rates"]["blocked_rate_percent"] == 20.0
    assert result["rates"]["overdue_rate_percent"] == 20.0
    assert result["rates"]["closure_archive_conversion_percent"] == 66.67
    assert result["rates"]["reopen_rate_percent"] == 50.0
    assert result["stage_duration_metrics"]["closure_review"]["average_hours"] == 4.0
    assert result["stage_duration_metrics"]["closed"]["average_hours"] == 2.0
    assert result["stage_duration_metrics"]["retention_pending_archive"]["median_hours"] == 4.0
    assert result["reviewer_throughput"][0]["reviewer"] == "alice"
    assert result["reviewer_throughput"][0]["completed_reviews"] == 4
    assert result["reviewer_throughput"][0]["completion_rate_percent"] == 50.0
    assert [item["days"] for item in result["trend_windows"]] == [7, 30]
    assert result["trend_windows"][0]["archive_completions"] == 2
    assert result["trend_windows"][0]["reopen_completions"] == 1
    assert result["source_records_mutated"] is False
    assert result["metrics_record_created"] is False


def test_v24_5_handles_empty_portfolio_and_window_fallback(monkeypatch):
    monkeypatch.setenv("SOCMINT_PORTFOLIO_TREND_WINDOWS", "bad,0")
    monkeypatch.setattr(service, "build_portfolio_operations_dashboard", lambda: {"counts": {}, "cases": []})
    monkeypatch.setattr(service, "build_case_status_stage_overview", lambda now=None: {"cases": []})
    monkeypatch.setattr(service, "build_workload_assignment_monitoring", lambda now=None: {"reviewers": []})
    monkeypatch.setattr(service, "build_blocked_overdue_case_queue", lambda: {"queue": []})
    monkeypatch.setattr(service, "_case_events", lambda: {})

    result = service.build_operational_metrics(
        now=dt.datetime(2026, 6, 15, 12, 0, tzinfo=dt.UTC)
    )
    assert result["case_volume"]["total_cases"] == 0
    assert result["rates"] == {
        "blocked_rate_percent": 0.0,
        "overdue_rate_percent": 0.0,
        "closure_archive_conversion_percent": 0.0,
        "reopen_rate_percent": 0.0,
    }
    assert [item["days"] for item in result["trend_windows"]] == [7, 30, 90]
    assert result["reviewer_throughput"] == []
