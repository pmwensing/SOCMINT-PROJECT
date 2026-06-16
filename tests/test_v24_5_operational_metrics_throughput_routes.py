from pathlib import Path

from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import register_dossier_assembly_routes_v21_0


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def test_v24_5_metrics_api_and_dashboard(tmp_path, monkeypatch):
    from src.socmint import portfolio_operations_routes_v24_0 as routes

    monkeypatch.setattr(routes, "build_portfolio_operations_dashboard", lambda: {
        "schema": "socmint.portfolio_operations_dashboard.v24_0",
        "version": "v24.0.0",
        "status": "ready",
        "counts": {"total": 1, "active": 1, "blocked": 0, "delivered": 0, "closed": 0, "archived": 0, "reopened": 0, "unstarted": 0},
        "stage_counts": {"active": 1},
        "cases": [],
        "blocked_cases": [],
        "source_records_mutated": False,
        "portfolio_record_created": False,
        "next_action": "review_portfolio_operations",
    })
    monkeypatch.setattr(routes, "build_case_status_stage_overview", lambda: {
        "schema": "socmint.portfolio_case_stage_overview.v24_1",
        "version": "v24.1.0",
        "status": "ready",
        "stage_model": ["unstarted", "active"],
        "stage_counts": {"active": 1},
        "cases": [],
        "case_count": 1,
        "blocked_count": 0,
        "source_records_mutated": False,
        "stage_record_created": False,
        "next_action": "review_case_stage_overview",
    })
    monkeypatch.setattr(routes, "build_workload_assignment_monitoring", lambda: {
        "schema": "socmint.portfolio_workload_assignment_monitoring.v24_2",
        "version": "v24.2.0",
        "status": "balanced",
        "generated_at": "2026-06-15T22:00:00+00:00",
        "counts": {"total_decisions": 0, "active_workload": 0, "assigned_active": 0, "unassigned_active": 0, "reviewer_count": 0},
        "review_state_counts": {},
        "reviewers": [],
        "entries": [],
        "unassigned_work": [],
        "workload_balance": {"minimum_active_workload": 0, "maximum_active_workload": 0, "average_active_workload": 0.0, "workload_spread": 0, "imbalanced": False, "overloaded_threshold": 0},
        "links": {"supervisor_queue": "/case-intelligence-review/supervisor-queue", "reviewer_queue": "/case-intelligence-review/my-assignments"},
        "source_assignments_mutated": False,
        "workload_record_created": False,
        "next_action": "monitor_reviewer_workload",
    })
    monkeypatch.setattr(routes, "build_blocked_overdue_case_queue", lambda: {
        "schema": "socmint.portfolio_blocked_overdue_queue.v24_3",
        "version": "v24.3.0",
        "status": "clear",
        "thresholds": {"stage_overdue_hours": 72.0, "assignment_overdue_hours": 48.0},
        "counts": {"total": 0, "critical": 0, "high": 0, "medium": 0, "low": 0, "blocked": 0, "stage_overdue": 0, "assignment_overdue": 0},
        "queue": [],
        "source_records_mutated": False,
        "queue_record_created": False,
        "next_action": "monitor_portfolio",
    })
    monkeypatch.setattr(routes, "build_escalation_control_state", lambda: {
        "schema": "socmint.portfolio_supervisor_escalation.v24_4",
        "version": "v24.4.0",
        "status": "clear",
        "items": [],
        "item_count": 0,
        "source_records_mutated": False,
        "next_action": "monitor_portfolio",
    })
    metrics = {
        "schema": "socmint.portfolio_operational_metrics.v24_5",
        "version": "v24.5.0",
        "status": "ready",
        "generated_at": "2026-06-15T22:00:00+00:00",
        "case_volume": {"total_cases": 5, "active_cases": 1, "completed_cases": 4, "blocked_cases": 1, "overdue_cases": 1},
        "completion_counts": {"delivered": 1, "closed": 3, "archived": 2, "reopened": 1},
        "stage_throughput": {"closed": 3, "archived": 2, "reopened": 1},
        "current_stage_counts": {"active": 1, "archived": 2},
        "stage_duration_metrics": {
            "active": {"count": 2, "average_hours": 8.0, "median_hours": 8.0, "minimum_hours": 4.0, "maximum_hours": 12.0},
            "closed": {"count": 1, "average_hours": 2.0, "median_hours": 2.0, "minimum_hours": 2.0, "maximum_hours": 2.0},
        },
        "reviewer_throughput": [{"reviewer": "alice", "completed_reviews": 4, "active_workload": 2, "total_assigned": 8, "completion_rate_percent": 50.0, "average_assignment_age_hours": 10.0}],
        "rates": {"blocked_rate_percent": 20.0, "overdue_rate_percent": 20.0, "closure_archive_conversion_percent": 66.67, "reopen_rate_percent": 50.0},
        "trend_windows": [{"days": 7, "window_start": "2026-06-08T22:00:00+00:00", "window_end": "2026-06-15T22:00:00+00:00", "event_count": 10, "active_case_count": 5, "stage_throughput": {"closed": 3}, "closure_completions": 3, "archive_completions": 2, "reopen_completions": 1}],
        "source_records_mutated": False,
        "metrics_record_created": False,
        "next_action": "review_operational_metrics",
    }
    monkeypatch.setattr(routes, "build_operational_metrics", lambda: metrics)

    client = _app(tmp_path, monkeypatch).test_client()
    assert client.get("/api/v1/portfolio-operations/metrics").status_code == 401

    with client.session_transaction() as sess:
        sess["user"] = "manager"

    ui = client.get("/portfolio-operations")
    api = client.get("/api/v1/portfolio-operations/metrics")

    assert ui.status_code == 200
    assert b"Operational Metrics and Throughput" in ui.data
    assert b"Case volume" in ui.data
    assert b"Blocked rate" in ui.data
    assert b"Closure" in ui.data and b"archive" in ui.data
    assert b"Reviewer Throughput" in ui.data
    assert b"Trend Windows" in ui.data
    assert b"alice" in ui.data
    assert b"v24.5 calculates operational metrics and throughput" in ui.data
    assert api.status_code == 200
    assert api.get_json()["rates"]["reopen_rate_percent"] == 50.0


def test_v24_5_release_note_and_no_migration():
    note = Path("release/V24_5_OPERATIONAL_METRICS_THROUGHPUT.md").read_text(encoding="utf-8")
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v24_5*")
    ]
    assert "case volume" in note
    assert "stage throughput" in note
    assert "completion counts" in note
    assert "average and median stage duration" in note
    assert "reviewer throughput" in note
    assert "blocked rate" in note
    assert "overdue rate" in note
    assert "closure-to-archive conversion" in note
    assert "reopen rate" in note
    assert "trend windows" in note
    assert "read-only" in note
    assert migrations == []
