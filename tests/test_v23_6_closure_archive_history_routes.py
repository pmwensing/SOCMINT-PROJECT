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


def test_v23_6_routes_and_ui(tmp_path, monkeypatch):
    from src.socmint import case_closure_history_routes_v23_6 as routes

    payload = {
        "case_id": "case-alpha",
        "status": "complete",
        "current_closure_state": "closed",
        "current_archive_state": "generated",
        "reopen_status": "none",
        "unresolved_action_count": 0,
        "unresolved_actions": [],
        "retention_disposition": {
            "disposition": "retain_until_expiration",
            "archive_class": "standard",
            "retention_years": 7,
            "retention_expires_at": "2033-06-14T20:10:00",
            "legal_hold": False,
        },
        "event_count": 2,
        "timeline": [
            {
                "timeline_id": 1,
                "event_type": "closure_decision",
                "actor": "supervisor",
                "occurred_at": "2026-06-14T20:10:00",
                "details": {"decision": "close"},
            },
            {
                "timeline_id": 2,
                "event_type": "archive_generation",
                "actor": "records",
                "occurred_at": "2026-06-14T20:30:00",
                "details": {"archive_package_id": "archive-1"},
            },
        ],
        "latest_events": {},
        "source_records_mutated": False,
        "history_record_created": False,
        "next_action": "product_review_checkpoint",
    }
    monkeypatch.setattr(routes, "build_case_closure_history", lambda case_id: payload)

    client = _app(tmp_path, monkeypatch).test_client()
    assert client.get("/api/v1/case-closure/case-alpha/history").status_code == 401

    with client.session_transaction() as sess:
        sess["user"] = "supervisor"

    ui = client.get("/case-closure/case-alpha/history")
    api = client.get("/api/v1/case-closure/case-alpha/history")

    assert ui.status_code == 200
    assert b"Closure and Archive History" in ui.data
    assert b"Current Lifecycle State" in ui.data
    assert b"Retention Disposition" in ui.data
    assert b"Ordered Case Timeline" in ui.data
    assert (
        b"read-only and does not create or alter readiness, closure, retention, archive, or reopen records"
        in ui.data
    )
    assert api.status_code == 200
    assert api.get_json()["current_archive_state"] == "generated"
    assert api.get_json()["event_count"] == 2


def test_v23_6_release_note_and_no_migration():
    note = Path("release/V23_6_CLOSURE_ARCHIVE_HISTORY.md").read_text(encoding="utf-8")
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v23_6*")
    ]
    assert "one ordered case timeline" in note
    assert "current closure state" in note
    assert "current archive state" in note
    assert "retention disposition" in note
    assert "reopen status" in note
    assert "unresolved actions" in note
    assert "read-only" in note
    assert migrations == []
