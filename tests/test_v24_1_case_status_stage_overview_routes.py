from pathlib import Path

from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import register_dossier_assembly_routes_v21_0


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def test_v24_1_stage_overview_api_and_dashboard(tmp_path, monkeypatch):
    from src.socmint import portfolio_operations_routes_v24_0 as routes

    portfolio = {
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
    }
    overview = {
        "schema": "socmint.portfolio_case_stage_overview.v24_1",
        "version": "v24.1.0",
        "status": "ready",
        "stage_model": ["unstarted", "active", "closure_review", "dossier_exported", "delivered", "closed", "retention_pending_archive", "archived", "reopened"],
        "stage_counts": {"closure_review": 1},
        "cases": [{
            "case_id": "case-alpha",
            "current_stage": "closure_review",
            "prior_stage": "active",
            "stage_entered_at": "2026-06-15T10:00:00+00:00",
            "stage_duration_seconds": 7200,
            "stage_duration_hours": 2.0,
            "progress_position": 3,
            "progress_total": 9,
            "progress_percent": 33.3,
            "blocked": True,
            "blocking_reason": "delivery_acknowledgement_required",
            "blockers": [{"key": "delivery_acknowledgement_required"}],
            "next_expected_action": "resolve_blocking_reason",
            "transitions": [],
            "latest_activity_at": "2026-06-15T10:00:00+00:00",
        }],
        "case_count": 1,
        "blocked_count": 1,
        "source_records_mutated": False,
        "stage_record_created": False,
        "next_action": "review_case_stage_overview",
    }
    monkeypatch.setattr(routes, "build_portfolio_operations_dashboard", lambda: portfolio)
    monkeypatch.setattr(routes, "build_case_status_stage_overview", lambda: overview)

    client = _app(tmp_path, monkeypatch).test_client()
    assert client.get("/api/v1/portfolio-operations/stage-overview").status_code == 401

    with client.session_transaction() as sess:
        sess["user"] = "manager"

    ui = client.get("/portfolio-operations")
    api = client.get("/api/v1/portfolio-operations/stage-overview")

    assert ui.status_code == 200
    assert b"Case Status and Stage Overview" in ui.data
    assert b"Current stage" in ui.data
    assert b"Prior stage" in ui.data
    assert b"Next expected action" in ui.data
    assert b"delivery_acknowledgement_required" in ui.data
    assert api.status_code == 200
    assert api.get_json()["cases"][0]["progress_position"] == 3


def test_v24_1_release_note_and_no_migration():
    note = Path("release/V24_1_CASE_STATUS_STAGE_OVERVIEW.md").read_text(encoding="utf-8")
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v24_1*")
    ]
    assert "single operational stage model" in note
    assert "prior stage" in note
    assert "stage-entry timestamp" in note
    assert "stage duration" in note
    assert "progress position" in note
    assert "blocking reason" in note
    assert "next expected action" in note
    assert "read-only" in note
    assert migrations == []
