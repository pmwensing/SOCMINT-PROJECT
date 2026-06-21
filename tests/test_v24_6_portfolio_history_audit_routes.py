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


def test_v24_6_history_routes_and_ui(tmp_path, monkeypatch):
    from src.socmint import portfolio_operations_routes_v24_0 as routes

    payload = {
        "schema": "socmint.portfolio_history_audit.v24_6",
        "version": "v24.6.0",
        "status": "ready",
        "generated_at": "2026-06-16T01:00:00+00:00",
        "history": [
            {
                "history_event_id": "audit-1",
                "event_type": "assignment",
                "occurred_at": "2026-06-15T20:00:00+00:00",
                "actor": "supervisor",
                "case_id": "case-alpha",
                "source_action": "case_intelligence_review_decision_assignment",
                "source_record_id": 1,
                "source_binding_sha256": "a" * 64,
            },
            {
                "history_event_id": "metrics-1",
                "event_type": "metrics_checkpoint",
                "occurred_at": "2026-06-16T01:00:00+00:00",
                "actor": "system",
                "case_id": None,
                "source_action": None,
                "source_record_id": None,
                "source_binding_sha256": "b" * 64,
            },
        ],
        "event_count": 2,
        "event_type_counts": {"assignment": 1, "metrics_checkpoint": 1},
        "actor_counts": {"supervisor": 1, "system": 1},
        "case_count": 1,
        "source_bound_event_count": 2,
        "current_portfolio_state": {
            "portfolio": {"status": "ready", "counts": {"total": 1}},
            "stages": {"case_count": 1, "blocked_count": 0},
            "assignments": {"status": "balanced"},
            "blocked_overdue": {"status": "clear"},
            "metrics": {"case_volume": {"total_cases": 1}},
        },
        "current_portfolio_state_sha256": "c" * 64,
        "source_records_mutated": False,
        "history_record_created": False,
        "next_action": "review_portfolio_history",
    }
    monkeypatch.setattr(routes, "build_portfolio_history_audit", lambda: payload)

    client = _app(tmp_path, monkeypatch).test_client()
    assert client.get("/api/v1/portfolio-operations/history").status_code == 401
    assert client.get("/portfolio-operations/history").status_code in {302, 303}

    with client.session_transaction() as sess:
        sess["user"] = "manager"

    ui = client.get("/portfolio-operations/history")
    api = client.get("/api/v1/portfolio-operations/history")

    assert ui.status_code == 200
    assert b"Portfolio History and Audit" in ui.data
    assert b"Current Portfolio State" in ui.data
    assert b"Ordered Operational History" in ui.data
    assert b"case-alpha" in ui.data
    assert b"supervisor" in ui.data
    assert b"source binding" in ui.data.lower()
    assert b"creates no portfolio-history record" in ui.data
    assert api.status_code == 200
    assert api.get_json()["event_count"] == 2
    assert api.get_json()["current_portfolio_state_sha256"] == "c" * 64


def test_v24_6_release_note_and_no_migration():
    note = Path("release/V24_6_PORTFOLIO_HISTORY_AUDIT.md").read_text(encoding="utf-8")
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v24_6*")
    ]
    assert "portfolio snapshots" in note
    assert "stage transitions" in note
    assert "assignments" in note
    assert "blockers" in note
    assert "overdue detections" in note
    assert "escalation controls" in note
    assert "metrics checkpoints" in note
    assert "one ordered operational history" in note
    assert "actor" in note
    assert "source binding" in note
    assert "event counts" in note
    assert "current portfolio state" in note
    assert "read-only" in note
    assert migrations == []
