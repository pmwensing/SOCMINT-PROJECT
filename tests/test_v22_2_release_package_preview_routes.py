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


def _preview():
    return {
        "status": "ready_for_acknowledgement",
        "release_ready": True,
        "section_count": 1,
        "attachment_count": 1,
        "restricted_section_count": 0,
        "restricted_attachment_count": 0,
        "blocker_count": 0,
        "blockers": [],
        "included_sections": [
            {
                "section_id": "key_findings",
                "title": "Key Findings",
                "classification": "internal",
                "redaction_required": False,
                "finding_count": 1,
            }
        ],
        "included_attachments": [
            {
                "attachment_id": "artifact-1",
                "path": "evidence/report.pdf",
                "media_type": "application/pdf",
                "classification": "internal",
                "redaction_required": False,
            }
        ],
    }


def test_v22_2_preview_routes_and_ui(tmp_path, monkeypatch):
    from src.socmint import dossier_release_workspace_routes_v22_0 as routes

    monkeypatch.setattr(
        routes, "build_dossier_release_workspace", lambda *a, **k: _workspace()
    )
    monkeypatch.setattr(routes, "latest_release_authorization", lambda case_id: None)
    monkeypatch.setattr(
        routes, "build_release_package_preview", lambda case_id: _preview()
    )
    monkeypatch.setattr(routes, "latest_release_preview", lambda case_id: None)
    monkeypatch.setattr(
        routes,
        "acknowledge_release_package_preview",
        lambda *a, **k: {
            "status": "acknowledged_ready",
            "preview_record_id": 41,
            "release_ready": True,
            "transmission_performed": False,
        },
    )

    client = _app(tmp_path, monkeypatch).test_client()
    assert (
        client.get("/api/v1/dossier-release/case-alpha/package-preview").status_code
        == 401
    )
    with client.session_transaction() as sess:
        sess["user"] = "operator"
        sess["_csrf_token"] = "test-csrf"

    ui = client.get("/dossier-release/case-alpha")
    api = client.get("/api/v1/dossier-release/case-alpha/package-preview")
    ack = client.post(
        "/api/v1/dossier-release/case-alpha/package-preview/acknowledge",
        json={"acknowledged": True, "note": "Reviewed."},
        headers={"X-CSRF-Token": "test-csrf"},
    )
    assert ui.status_code == 200
    assert b"Release Package Preview and Redaction Check" in ui.data
    assert b"Restricted sections" in ui.data
    assert b"I acknowledge the exact material" in ui.data
    assert b"does not transmit" in ui.data
    assert api.status_code == 200
    assert api.get_json()["section_count"] == 1
    assert ack.status_code == 200
    assert ack.get_json()["preview_record_id"] == 41
    assert ack.get_json()["transmission_performed"] is False


def test_v22_2_release_note_client_and_no_migration():
    note = Path("release/V22_2_RELEASE_PACKAGE_PREVIEW_REDACTION_CHECK.md").read_text(
        encoding="utf-8"
    )
    script = Path("src/socmint/static/dossier_release_workspace_v22_0.js").read_text(
        encoding="utf-8"
    )
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v22_2*")
    ]
    assert "exact material authorized for release" in note
    assert "redaction or sensitivity blockers" in note
    assert "operator acknowledgement" in note
    assert "without transmitting" in note
    assert "acknowledge-release-preview" in script
    assert migrations == []
