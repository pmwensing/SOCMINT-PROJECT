import datetime as dt

from src.socmint import portfolio_history_audit_v24_6 as service


def test_v24_6_builds_ordered_history_with_current_state(monkeypatch):
    now = dt.datetime(2026, 6, 16, 1, 0, tzinfo=dt.UTC)
    monkeypatch.setattr(service, "_audit_events", lambda: [
        {
            "history_event_id": "audit-1",
            "event_type": "assignment",
            "occurred_at": "2026-06-15T20:00:00+00:00",
            "actor": "supervisor",
            "case_id": "case-alpha",
            "source_action": "case_intelligence_review_decision_assignment",
            "source_record_id": 1,
            "source_binding": {"record_id": 1},
            "source_binding_sha256": "a" * 64,
            "details": {"assigned_reviewer": "alice"},
            "synthetic_checkpoint": False,
        },
        {
            "history_event_id": "audit-2",
            "event_type": "escalation_control",
            "occurred_at": "2026-06-15T22:00:00+00:00",
            "actor": "manager",
            "case_id": "case-alpha",
            "source_action": "portfolio_case_escalated",
            "source_record_id": 2,
            "source_binding": {"record_id": 2},
            "source_binding_sha256": "b" * 64,
            "details": {"control": "escalate"},
            "synthetic_checkpoint": False,
        },
    ])
    monkeypatch.setattr(service, "build_portfolio_operations_dashboard", lambda: {
        "schema": "socmint.portfolio_operations_dashboard.v24_0",
        "version": "v24.0.0",
        "status": "ready",
        "counts": {"total": 2, "active": 1, "blocked": 1},
        "stage_counts": {"active": 1, "archived": 1},
    })
    monkeypatch.setattr(service, "build_case_status_stage_overview", lambda now=None: {
        "schema": "socmint.portfolio_case_stage_overview.v24_1",
        "version": "v24.1.0",
        "status": "ready",
        "case_count": 2,
        "blocked_count": 1,
        "stage_counts": {"active": 1, "archived": 1},
    })
    monkeypatch.setattr(service, "build_workload_assignment_monitoring", lambda now=None: {
        "schema": "socmint.portfolio_workload_assignment_monitoring.v24_2",
        "version": "v24.2.0",
        "status": "attention_required",
        "counts": {"active_workload": 2, "unassigned_active": 1},
        "workload_balance": {"imbalanced": True},
    })
    monkeypatch.setattr(service, "build_blocked_overdue_case_queue", lambda: {
        "schema": "socmint.portfolio_blocked_overdue_queue.v24_3",
        "version": "v24.3.0",
        "status": "attention_required",
        "counts": {"total": 1, "critical": 1},
        "thresholds": {"stage_overdue_hours": 72.0, "assignment_overdue_hours": 48.0},
    })
    monkeypatch.setattr(service, "build_operational_metrics", lambda now=None: {
        "schema": "socmint.portfolio_operational_metrics.v24_5",
        "version": "v24.5.0",
        "status": "ready",
        "case_volume": {"total_cases": 2},
        "completion_counts": {"archived": 1},
        "rates": {"blocked_rate_percent": 50.0},
    })

    result = service.build_portfolio_history_audit(now=now)

    assert result["status"] == "ready"
    assert result["event_count"] == 7
    assert result["event_type_counts"]["assignment"] == 1
    assert result["event_type_counts"]["escalation_control"] == 1
    assert result["event_type_counts"]["portfolio_snapshot"] == 1
    assert result["event_type_counts"]["stage_snapshot"] == 1
    assert result["event_type_counts"]["assignment_snapshot"] == 1
    assert result["event_type_counts"]["blocked_overdue_detection"] == 1
    assert result["event_type_counts"]["metrics_checkpoint"] == 1
    assert result["actor_counts"] == {"manager": 1, "supervisor": 1, "system": 5}
    assert result["case_count"] == 1
    assert result["source_bound_event_count"] == 7
    assert result["history"][0]["history_event_id"] == "audit-1"
    assert result["history"][-1]["synthetic_checkpoint"] is True
    assert result["current_portfolio_state"]["portfolio"]["counts"]["total"] == 2
    assert result["current_portfolio_state"]["blocked_overdue"]["counts"]["critical"] == 1
    assert len(result["current_portfolio_state_sha256"]) == 64
    assert result["source_records_mutated"] is False
    assert result["history_record_created"] is False


def test_v24_6_checkpoint_ids_are_deterministic():
    source = {"schema": "x", "version": "1", "status": "ready", "value": 3}
    first = service._checkpoint("metrics_checkpoint", "2026-06-16T01:00:00+00:00", source)
    second = service._checkpoint("metrics_checkpoint", "2026-06-16T01:00:00+00:00", source)
    assert first["history_event_id"] == second["history_event_id"]
    assert first["source_binding_sha256"] == second["source_binding_sha256"]
    assert first["synthetic_checkpoint"] is True
