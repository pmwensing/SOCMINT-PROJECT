from pathlib import Path

from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import register_dossier_assembly_routes_v21_0


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def _workspace():
    return {
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
        "recipient_catalog": [],
        "available_channels": ["secure_portal"],
        "package_ready": True,
        "selection_ready": True,
        "blocker_count": 0,
        "blockers": [],
        "case_delivery_workspace": {
            "href": "/case-delivery?case_id=case-alpha",
            "handoff_context": {},
        },
    }


def _preview():
    return {
        "section_count": 1,
        "attachment_count": 0,
        "restricted_section_count": 0,
        "blocker_count": 0,
        "blockers": [],
        "included_sections": [],
        "included_attachments": [],
    }


def test_v22_3_routes_and_ui(tmp_path, monkeypatch):
    from src.socmint import dossier_release_workspace_routes_v22_0 as routes

    monkeypatch.setattr(routes, "build_dossier_release_workspace", lambda *a, **k: _workspace())
    monkeypatch.setattr(routes, "latest_release_authorization", lambda case_id: None)
    monkeypatch.setattr(routes, "build_release_package_preview", lambda case_id: _preview())
    monkeypatch.setattr(routes, "latest_release_preview", lambda case_id: None)
    monkeypatch.setattr(routes, "build_secure_distribution_readiness", lambda case_id: {
        "status": "ready_for_final_confirmation",
        "ready": True,
        "blocker_count": 0,
        "blockers": [],
        "latest_distribution": None,
    })
    monkeypatch.setattr(routes, "dispatch_secure_distribution", lambda *a, **k: {
        "status": "dispatch_recorded",
        "distribution_record_id": 51,
        "transport_invoked": True,
        "transport_engine": "existing_case_delivery_operations_v16_0",
    })

    client = _app(tmp_path, monkeypatch).test_client()
    assert client.get(
        "/api/v1/dossier-release/case-alpha/distribution-readiness"
    ).status_code == 401
    with client.session_transaction() as sess:
        sess["user"] = "operator"
        sess["_csrf_token"] = "test-csrf"

    ui = client.get("/dossier-release/case-alpha")
    readiness = client.get(
        "/api/v1/dossier-release/case-alpha/distribution-readiness"
    )
    dispatched = client.post(
        "/api/v1/dossier-release/case-alpha/dispatch",
        json={"confirmed": True, "note": "Dispatch now."},
        headers={"X-CSRF-Token": "test-csrf"},
    )
    assert ui.status_code == 200
    assert b"Secure Distribution Action" in ui.data
    assert b"explicitly confirm final dispatch" in ui.data
    assert b"existing case-delivery execution path" in ui.data
    assert readiness.status_code == 200
    assert readiness.get_json()["ready"] is True
    assert dispatched.status_code == 200
    assert dispatched.get_json()["distribution_record_id"] == 51


def test_v22_3_release_note_client_and_no_migration():
    note = Path("release/V22_3_SECURE_DISTRIBUTION_ACTION.md").read_text(encoding="utf-8")
    script = Path("src/socmint/static/dossier_release_workspace_v22_0.js").read_text(encoding="utf-8")
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v22_3*")
    ]
    assert "latest valid authorization" in note
    assert "acknowledged-ready preview" in note
    assert "explicit final operator confirmation" in note
    assert "existing case-delivery execution path" in note
    assert "dispatch-secure-distribution" in script
    assert migrations == []
