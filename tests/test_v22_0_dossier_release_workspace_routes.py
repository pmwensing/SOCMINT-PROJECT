from pathlib import Path

from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import register_dossier_assembly_routes_v21_0


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def _payload(ready=True):
    return {
        "schema": "socmint.dossier_release_workspace.v22_0",
        "version": "v22.0.0",
        "case_id": "case-alpha",
        "status": "ready_for_delivery_workspace" if ready else "needs_configuration",
        "release_ready": ready,
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
            "authorized": True,
            "allowed_channels": ["secure_portal"],
        }],
        "selected_recipient": None,
        "available_channels": ["secure_portal"],
        "selected_channel": None,
        "package_ready": True,
        "selection_ready": ready,
        "blocker_count": 0 if ready else 1,
        "blockers": [] if ready else [{"key": "delivery_channel_required"}],
        "case_delivery_workspace": {
            "href": "/case-delivery?case_id=case-alpha",
            "api_href": "/api/v1/case-delivery/case-alpha",
            "handoff_context": {},
        },
    }


def test_v22_0_routes_and_ui(tmp_path, monkeypatch):
    from src.socmint import dossier_release_workspace_routes_v22_0 as routes
    monkeypatch.setattr(routes, "build_dossier_release_workspace", lambda *a, **k: _payload(True))
    client = _app(tmp_path, monkeypatch).test_client()
    assert client.get("/api/v1/dossier-release/case-alpha").status_code == 401
    with client.session_transaction() as sess:
        sess["user"] = "operator"
        sess["_csrf_token"] = "test-csrf"
    api = client.get("/api/v1/dossier-release/case-alpha")
    ui = client.get("/dossier-release/case-alpha")
    preview = client.post(
        "/api/v1/dossier-release/case-alpha/preview",
        json={"recipient_id": "recipient-1", "delivery_channel": "secure_portal"},
        headers={"X-CSRF-Token": "test-csrf"},
    )
    assert api.status_code == 200
    assert ui.status_code == 200
    assert b"Dossier Release Workspace" in ui.data
    assert b"Authorized recipient" in ui.data
    assert b"Delivery channel" in ui.data
    assert b"Open Case Delivery Workspace" in ui.data
    assert b"does not transmit" in ui.data
    assert preview.status_code == 200
    assert preview.get_json()["transmission_performed"] is False


def test_v22_0_release_note_client_and_no_migration():
    note = Path("release/V22_0_DOSSIER_RELEASE_WORKSPACE.md").read_text(encoding="utf-8")
    script = Path("src/socmint/static/dossier_release_workspace_v22_0.js").read_text(encoding="utf-8")
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v22_0*")
    ]
    assert "latest approved v21.6 export package" in note
    assert "authorized recipient" in note
    assert "delivery-channel selection" in note
    assert "without transmitting" in note
    assert "preview-release-readiness" in script
    assert migrations == []
