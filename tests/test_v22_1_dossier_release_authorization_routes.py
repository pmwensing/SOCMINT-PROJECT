from pathlib import Path

from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import register_dossier_assembly_routes_v21_0


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def test_v22_1_authorization_route_and_ui(tmp_path, monkeypatch):
    from src.socmint import dossier_release_workspace_routes_v22_0 as routes

    workspace = {
        "case_id": "case-alpha",
        "status": "ready_for_delivery_workspace",
        "release_ready": True,
        "transmission_performed": False,
        "export_package": {
            "export_package_id": "dossier-export-1",
            "export_package_sha256": "a" * 64,
            "export_record_id": 21,
        },
        "approval_state": {"approval_id": "approval-1"},
        "integrity_state": {"content_sha256": "b" * 64},
        "recipient_catalog": [{
            "recipient_id": "recipient-1",
            "display_name": "Authorized Recipient",
            "organization": "Example Agency",
            "allowed_channels": ["secure_portal"],
        }],
        "selected_recipient": None,
        "available_channels": ["secure_portal"],
        "selected_channel": None,
        "package_ready": True,
        "selection_ready": False,
        "blocker_count": 0,
        "blockers": [],
        "case_delivery_workspace": {
            "href": "/case-delivery?case_id=case-alpha",
            "handoff_context": {},
        },
    }
    monkeypatch.setattr(routes, "build_dossier_release_workspace", lambda *a, **k: workspace)
    monkeypatch.setattr(routes, "latest_release_authorization", lambda case_id: None)
    monkeypatch.setattr(routes, "authorize_dossier_release", lambda *a, **k: {
        "status": "authorized",
        "authorization_record_id": 31,
        "transmission_performed": False,
    })

    client = _app(tmp_path, monkeypatch).test_client()
    with client.session_transaction() as sess:
        sess["user"] = "operator"
        sess["_csrf_token"] = "test-csrf"

    ui = client.get("/dossier-release/case-alpha")
    response = client.post(
        "/api/v1/dossier-release/case-alpha/authorize",
        json={
            "recipient_id": "recipient-1",
            "delivery_channel": "secure_portal",
            "confirmed": True,
            "note": "Authorized.",
        },
        headers={"X-CSRF-Token": "test-csrf"},
    )
    assert ui.status_code == 200
    assert b"Recipient and Delivery Authorization" in ui.data
    assert b"explicitly confirm" in ui.data
    assert b"does not transmit" in ui.data
    assert response.status_code == 200
    assert response.get_json()["authorization_record_id"] == 31
    assert response.get_json()["transmission_performed"] is False


def test_v22_1_release_note_client_and_no_migration():
    note = Path("release/V22_1_RECIPIENT_DELIVERY_AUTHORIZATION.md").read_text(encoding="utf-8")
    script = Path("src/socmint/static/dossier_release_workspace_v22_0.js").read_text(encoding="utf-8")
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v22_1*")
    ]
    assert "explicit operator confirmation" in note
    assert "immutable authorization" in note
    assert "case-delivery workspace" in note
    assert "without transmitting" in note
    assert "authorize-release-selection" in script
    assert migrations == []
