from pathlib import Path

from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import (
    register_dossier_assembly_routes_v21_0,
)


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def test_v24_3_queue_api_and_dashboard(tmp_path, monkeypatch):
    from src.socmint import portfolio_operations_routes_v24_0 as routes

    portfolio = {
        "schema": "socmint.portfolio_operations_dashboard.v24_0",
        "version": "v24.0.0",
        "status": "ready",
        "counts": {
            "total": 0,
            "active": 0,
            "blocked": 0,
            "delivered": 0,
            "closed": 0,
            "archived": 0,
            "reopened": 0,
            "unstarted": 0,
        },
        "stage_counts": {},
        "cases": [],
        "blocked_cases": [],
        "source_records_mutated": False,
        "portfolio_record_created": False,
        "next_action": "review_portfolio_operations",
    }
    stage = {
        "schema": "socmint.portfolio_case_stage_overview.v24_1",
        "version": "v24.1.0",
        "status": "ready",
        "stage_model": ["unstarted", "active"],
        "stage_counts": {},
        "cases": [],
        "case_count": 0,
        "blocked_count": 0,
        "source_records_mutated": False,
        "stage_record_created": False,
        "next_action": "review_case_stage_overview",
    }
    workload = {
        "schema": "socmint.portfolio_workload_assignment_monitoring.v24_2",
        "version": "v24.2.0",
        "status": "balanced",
        "generated_at": "2026-06-15T18:00:00+00:00",
        "counts": {
            "total_decisions": 0,
            "active_workload": 0,
            "assigned_active": 0,
            "unassigned_active": 0,
            "reviewer_count": 0,
        },
        "review_state_counts": {},
        "reviewers": [],
        "entries": [],
        "unassigned_work": [],
        "workload_balance": {
            "minimum_active_workload": 0,
            "maximum_active_workload": 0,
            "average_active_workload": 0.0,
            "workload_spread": 0,
            "imbalanced": False,
            "overloaded_threshold": 0,
        },
        "links": {
            "supervisor_queue": "/case-intelligence-review/supervisor-queue",
            "reviewer_queue": "/case-intelligence-review/my-assignments",
        },
        "source_assignments_mutated": False,
        "workload_record_created": False,
        "next_action": "monitor_reviewer_workload",
    }
    blocked = {
        "schema": "socmint.portfolio_blocked_overdue_queue.v24_3",
        "version": "v24.3.0",
        "status": "attention_required",
        "thresholds": {"stage_overdue_hours": 72.0, "assignment_overdue_hours": 48.0},
        "counts": {
            "total": 1,
            "critical": 1,
            "high": 0,
            "medium": 0,
            "low": 0,
            "blocked": 1,
            "stage_overdue": 1,
            "assignment_overdue": 1,
        },
        "queue": [
            {
                "case_id": "case-alpha",
                "severity": "critical",
                "severity_rank": 4,
                "current_stage": "closure_review",
                "stage_age_hours": 160.0,
                "stage_overdue": True,
                "stage_overdue_by_hours": 88.0,
                "assignment_age_hours": 100.0,
                "assignment_overdue": True,
                "assignment_overdue_by_hours": 52.0,
                "blocked": True,
                "blocking_reason": "delivery_acknowledgement_required",
                "blockers": [{"key": "delivery_acknowledgement_required"}],
                "owner": "owner-a",
                "assigned_reviewers": ["alice"],
                "active_assignment_count": 1,
                "review_states": ["unreviewed"],
                "next_expected_action": "resolve_blocking_reason",
                "remediation_links": {
                    "case_review": "/case-intelligence-review/case-alpha",
                    "dossier_assembly": "/dossier-assembly/case-alpha",
                    "closure_workspace": "/case-closure/case-alpha",
                    "closure_history": "/case-closure/case-alpha/history",
                    "supervisor_queue": "/case-intelligence-review/supervisor-queue?case_id=case-alpha",
                    "reviewer_queue": "/case-intelligence-review/my-assignments",
                },
            }
        ],
        "source_records_mutated": False,
        "queue_record_created": False,
        "next_action": "remediate_highest_priority_case",
    }

    monkeypatch.setattr(
        routes, "build_portfolio_operations_dashboard", lambda: portfolio
    )
    monkeypatch.setattr(routes, "build_case_status_stage_overview", lambda: stage)
    monkeypatch.setattr(
        routes, "build_workload_assignment_monitoring", lambda: workload
    )
    monkeypatch.setattr(routes, "build_blocked_overdue_case_queue", lambda: blocked)

    client = _app(tmp_path, monkeypatch).test_client()
    assert client.get("/api/v1/portfolio-operations/blocked-overdue").status_code == 401

    with client.session_transaction() as sess:
        sess["user"] = "manager"

    ui = client.get("/portfolio-operations")
    api = client.get("/api/v1/portfolio-operations/blocked-overdue")

    assert ui.status_code == 200
    assert b"Blocked and Overdue Case Queue" in ui.data
    assert b"Critical" in ui.data
    assert b"case-alpha" in ui.data
    assert b"delivery_acknowledgement_required" in ui.data
    assert b"owner-a" in ui.data
    assert b"alice" in ui.data
    assert b"v24.3 prioritizes blocked and overdue cases" in ui.data
    assert api.status_code == 200
    assert api.get_json()["queue"][0]["severity"] == "critical"


def test_v24_3_release_note_and_no_migration():
    note = Path("release/V24_3_BLOCKED_OVERDUE_CASE_QUEUE.md").read_text(
        encoding="utf-8"
    )
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v24_3*")
    ]
    assert "portfolio blockers" in note
    assert "stage age" in note
    assert "assignment age" in note
    assert "overdue thresholds" in note
    assert "severity" in note
    assert "owner and reviewer" in note
    assert "direct remediation links" in note
    assert "prioritized supervisor queue" in note
    assert "read-only" in note
    assert migrations == []
