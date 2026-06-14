from pathlib import Path

from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import register_dossier_assembly_routes_v21_0


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def test_v22_6_history_routes_and_ui(tmp_path, monkeypatch):
    from src.socmint import dossier_release_history_routes_v22_6 as routes

    payload = {
        "case_id": "case-alpha",
        "status": "closure_ready",
        "current_release_outcome": "delivered_and_acknowledged",
        "timeline_event_count": 4,
        "unresolved_action_count": 0,
        "unresolved_actions": [],
        "closure_ready": True,
        "closure_summary": {
            "case_id": "case-alpha",
            "release_outcome": "delivered_and_acknowledged",
            "closure_ready": True,
        },
        "timeline": [
            {
                "event_id": 1,
                "event_type": "authorization",
                "action": "case_dossier_release_authorization",
                "actor": "operator",
                "recorded_at": "2026-06-14T19:40:00",
                "details": {"authorization_id": "auth-1"},
            },
            {
                "event_id": 2,
                "event_type": "recipient_acknowledgement",
                "action": "case_dossier_recipient_acknowledgement",
                "actor": "operator",
                "recorded_at": "2026-06-14T19:45:00",
                "details": {"acknowledgement_id": "ack-1"},
            },
        ],
    }
    monkeypatch.setattr(routes, "build_release_delivery_history", lambda case_id: payload)

    client = _app(tmp_path, monkeypatch).test_client()
    assert client.get("/api/v1/dossier-release/case-alpha/history").status_code == 401
    with client.session_transaction() as sess:
        sess["user"] = "operator"

    ui = client.get("/dossier-release/case-alpha/history")
    api = client.get("/api/v1/dossier-release/case-alpha/history")
    assert ui.status_code == 200
    assert b"Release and Delivery History" in ui.data
    assert b"Case Closure Summary" in ui.data
    assert b"Consolidated Timeline" in ui.data
    assert b"delivered_and_acknowledged" in ui.data
    assert b"does not mutate authorization, preview, dispatch, receipt, acknowledgement, recall, or reissue records" in ui.data
    assert api.status_code == 200
    assert api.get_json()["closure_ready"] is True
    assert api.get_json()["timeline_event_count"] == 4


def test_v22_6_release_note_and_no_migration():
    note = Path("release/V22_6_RELEASE_DELIVERY_HISTORY_CASE_CLOSURE_SUMMARY.md").read_text(encoding="utf-8")
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v22_6*")
    ]
    assert "consolidated timeline" in note
    assert "current release outcome" in note
    assert "unresolved actions" in note
    assert "closure-ready summary" in note
    assert "without creating another narrow integrity wrapper" in note
    assert migrations == []
