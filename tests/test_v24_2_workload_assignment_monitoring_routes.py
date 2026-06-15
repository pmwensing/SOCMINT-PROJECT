from pathlib import Path

from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import register_dossier_assembly_routes_v21_0


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def test_v24_2_workload_api_and_dashboard(tmp_path, monkeypatch):
    from src.socmint import portfolio_operations_routes_v24_0 as routes

    portfolio = {
        "schema": "socmint.portfolio_operations_dashboard.v24_0",
        "version": "v24.0.0",
        "status": "ready",
        "counts": {"total": 0, "active": 0, "blocked": 0, "delivered": 0, "closed": 0, "archived": 0, "reopened": 0, "unstarted": 0},
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
        "status": "attention_required",
        "generated_at": "2026-06-15T14:00:00+00:00",
        "counts": {"total_decisions": 3, "active_workload": 2, "assigned_active": 1, "unassigned_active": 1, "reviewer_count": 1},
        "review_state_counts": {"unreviewed": 2},
        "reviewers": [{
            "reviewer": "alice",
            "total_assigned": 2,
            "active_workload": 1,
            "unreviewed": 1,
            "needs_follow_up": 0,
            "reviewed": 1,
            "accepted": 0,
            "oldest_assignment_age_hours": 4.0,
            "average_assignment_age_hours": 3.0,
            "reviewer_queue_href": "/case-intelligence-review/my-assignments",
            "supervisor_queue_href": "/case-intelligence-review/supervisor-queue?assigned_reviewer=alice",
            "workload_delta_from_average": 0.0,
            "workload_imbalanced": False,
            "overloaded": False,
        }],
        "entries": [],
        "unassigned_work": [{
            "case_id": "case-alpha",
            "decision": "accept",
            "review_state": "unreviewed",
            "age_hours": 8.0,
            "case_workspace_href": "/case-intelligence-review/case-alpha",
        }],
        "workload_balance": {
            "minimum_active_workload": 1,
            "maximum_active_workload": 1,
            "average_active_workload": 1.0,
            "workload_spread": 0,
            "imbalanced": False,
            "overloaded_threshold": 2,
        },
        "links": {
            "supervisor_queue": "/case-intelligence-review/supervisor-queue",
            "reviewer_queue": "/case-intelligence-review/my-assignments",
        },
        "source_assignments_mutated": False,
        "workload_record_created": False,
        "next_action": "assign_unassigned_work",
    }

    monkeypatch.setattr(routes, "build_portfolio_operations_dashboard", lambda: portfolio)
    monkeypatch.setattr(routes, "build_case_status_stage_overview", lambda: stage)
    monkeypatch.setattr(routes, "build_workload_assignment_monitoring", lambda: workload)

    client = _app(tmp_path, monkeypatch).test_client()
    assert client.get("/api/v1/portfolio-operations/workload-monitoring").status_code == 401

    with client.session_transaction() as sess:
        sess["user"] = "manager"

    ui = client.get("/portfolio-operations")
    api = client.get("/api/v1/portfolio-operations/workload-monitoring")

    assert ui.status_code == 200
    assert b"Workload and Assignment Monitoring" in ui.data
    assert b"Unassigned Work" in ui.data
    assert b"alice" in ui.data
    assert b"case-alpha" in ui.data
    assert b"Open Supervisor Queue" in ui.data
    assert b"Open My Assignments" in ui.data
    assert b"v24.2 monitors existing assignments" in ui.data
    assert api.status_code == 200
    assert api.get_json()["counts"]["unassigned_active"] == 1


def test_v24_2_release_note_and_no_migration():
    note = Path("release/V24_2_WORKLOAD_ASSIGNMENT_MONITORING.md").read_text(encoding="utf-8")
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v24_2*")
    ]
    assert "reviewer and supervisor assignments" in note
    assert "active workload" in note
    assert "unassigned work" in note
    assert "assignment age" in note
    assert "review state" in note
    assert "workload imbalance" in note
    assert "existing reviewer and supervisor queues" in note
    assert "read-only" in note
    assert migrations == []
