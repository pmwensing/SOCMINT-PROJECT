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


def test_v24_0_routes_and_ui(tmp_path, monkeypatch):
    from src.socmint import portfolio_operations_routes_v24_0 as routes

    payload = {
        "schema": "socmint.portfolio_operations_dashboard.v24_0",
        "version": "v24.0.0",
        "status": "ready",
        "counts": {
            "total": 2,
            "active": 1,
            "blocked": 1,
            "delivered": 0,
            "closed": 0,
            "archived": 1,
            "reopened": 0,
            "unstarted": 0,
        },
        "stage_counts": {"active": 1, "archived": 1},
        "cases": [
            {
                "case_id": "case-alpha",
                "stage": "active",
                "status": "blocked",
                "blocked": True,
                "blockers": [
                    {
                        "key": "citation_required",
                        "source_action": "dossier_quality_review",
                    }
                ],
                "event_count": 3,
                "latest_action": "dossier_quality_review",
                "latest_actor": "operator",
                "latest_activity_at": "2026-06-15T05:00:00",
                "retention_disposition": None,
                "links": {
                    "case_review": "/case-intelligence-review/case-alpha",
                    "dossier_assembly": "/dossier-assembly/case-alpha",
                    "release_workspace": "/dossier-release/case-alpha",
                    "closure_workspace": "/case-closure/case-alpha",
                    "closure_history": "/case-closure/case-alpha/history",
                    "delivery_workspace": "/case-delivery?case_id=case-alpha",
                },
            },
            {
                "case_id": "case-archive",
                "stage": "archived",
                "status": "operational",
                "blocked": False,
                "blockers": [],
                "event_count": 8,
                "latest_action": "case_archive_package_generated",
                "latest_actor": "supervisor",
                "latest_activity_at": "2026-06-15T06:00:00",
                "retention_disposition": None,
                "links": {
                    "case_review": "/case-intelligence-review/case-archive",
                    "dossier_assembly": "/dossier-assembly/case-archive",
                    "release_workspace": "/dossier-release/case-archive",
                    "closure_workspace": "/case-closure/case-archive",
                    "closure_history": "/case-closure/case-archive/history",
                    "delivery_workspace": "/case-delivery?case_id=case-archive",
                },
            },
        ],
        "blocked_cases": [],
        "source_records_mutated": False,
        "portfolio_record_created": False,
        "next_action": "review_portfolio_operations",
    }
    payload["blocked_cases"] = [payload["cases"][0]]
    monkeypatch.setattr(routes, "build_portfolio_operations_dashboard", lambda: payload)

    client = _app(tmp_path, monkeypatch).test_client()
    assert client.get("/api/v1/portfolio-operations").status_code == 401

    with client.session_transaction() as sess:
        sess["user"] = "manager"

    ui = client.get("/portfolio-operations")
    api = client.get("/api/v1/portfolio-operations")
    assert ui.status_code == 200
    assert b"Portfolio Operations Dashboard" in ui.data
    assert b"Portfolio Summary" in ui.data
    assert b"Case Operations" in ui.data
    assert b"Blocked Cases" in ui.data
    assert b"case-alpha" in ui.data
    assert b"citation_required" in ui.data
    assert b"v24.0 is read-only" in ui.data
    assert api.status_code == 200
    assert api.get_json()["counts"]["total"] == 2


def test_v24_0_release_note_and_no_migration():
    note = Path("release/V24_0_PORTFOLIO_OPERATIONS_DASHBOARD.md").read_text(
        encoding="utf-8"
    )
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v24_0*")
    ]
    assert "existing case-targeted audit events" in note
    assert (
        "active, blocked, delivered, closed, archived, reopened, and unstarted" in note
    )
    assert "direct navigation" in note
    assert "read-only" in note
    assert migrations == []
