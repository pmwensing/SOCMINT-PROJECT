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
        "export_package": {"export_package_id": "dossier-export-1", "export_package_sha256": "a" * 64, "export_record_id": 21},
        "approval_state": {"approval_id": "approval-1"},
        "integrity_state": {"content_sha256": "b" * 64},
        "recipient_catalog": [],
        "available_channels": ["secure_portal"],
        "package_ready": True,
        "selection_ready": True,
        "blocker_count": 0,
        "blockers": [],
        "case_delivery_workspace": {"href": "/case-delivery?case_id=case-alpha", "handoff_context": {}},
    }


def test_v22_4_routes_and_ui(tmp_path, monkeypatch):
    from src.socmint import dossier_release_workspace_routes_v22_0 as routes

    monkeypatch.setattr(routes, "build_dossier_release_workspace", lambda *a, **k: _workspace())
    monkeypatch.setattr(routes, "latest_release_authorization", lambda case_id: None)
    monkeypatch.setattr(routes, "build_release_package_preview", lambda case_id: {
        "section_count": 0, "attachment_count": 0, "restricted_section_count": 0,
        "blocker_count": 0, "blockers": [], "included_sections": [], "included_attachments": [],
    })
    monkeypatch.setattr(routes, "latest_release_preview", lambda case_id: None)
    monkeypatch.setattr(routes, "build_secure_distribution_readiness", lambda case_id: {
        "status": "ready_for_final_confirmation", "ready": True, "blocker_count": 0,
        "blockers": [], "latest_distribution": None,
    })
    monkeypatch.setattr(routes, "build_delivery_receipt_state", lambda case_id: {
        "status": "tracking", "delivery_succeeded": True,
        "acknowledgement_received": False, "acknowledgement_outstanding": True,
        "next_action": "record_recipient_acknowledgement",
        "latest_delivery_receipt": {"delivery_result": "delivered", "recorded_by": "operator", "recorded_at": "now"},
        "latest_recipient_acknowledgement": None,
    })
    monkeypatch.setattr(routes, "record_delivery_receipt", lambda *a, **k: {
        "status": "delivery_recorded", "delivery_receipt_record_id": 61,
        "dispatch_record_mutated": False,
    })
    monkeypatch.setattr(routes, "record_recipient_acknowledgement", lambda *a, **k: {
        "status": "acknowledgement_recorded", "acknowledgement_record_id": 62,
        "dispatch_record_mutated": False,
    })

    client = _app(tmp_path, monkeypatch).test_client()
    assert client.get("/api/v1/dossier-release/case-alpha/delivery-state").status_code == 401
    with client.session_transaction() as sess:
        sess["user"] = "operator"
        sess["_csrf_token"] = "test-csrf"

    ui = client.get("/dossier-release/case-alpha")
    state = client.get("/api/v1/dossier-release/case-alpha/delivery-state")
    receipt = client.post(
        "/api/v1/dossier-release/case-alpha/delivery-receipt",
        json={"delivery_result": "delivered", "provider_message_id": "provider-1"},
        headers={"X-CSRF-Token": "test-csrf"},
    )
    ack = client.post(
        "/api/v1/dossier-release/case-alpha/recipient-acknowledgement",
        json={"acknowledged": True, "recipient_name": "Recipient"},
        headers={"X-CSRF-Token": "test-csrf"},
    )
    assert ui.status_code == 200
    assert b"Delivery Receipt and Recipient Acknowledgement" in ui.data
    assert b"Acknowledgement outstanding" in ui.data
    assert b"original dispatch record is never changed" in ui.data
    assert state.status_code == 200
    assert state.get_json()["acknowledgement_outstanding"] is True
    assert receipt.status_code == 200
    assert receipt.get_json()["delivery_receipt_record_id"] == 61
    assert ack.status_code == 200
    assert ack.get_json()["acknowledgement_record_id"] == 62


def test_v22_4_release_note_client_and_no_migration():
    note = Path("release/V22_4_DELIVERY_RECEIPT_RECIPIENT_ACKNOWLEDGEMENT.md").read_text(encoding="utf-8")
    script = Path("src/socmint/static/dossier_release_workspace_v22_0.js").read_text(encoding="utf-8")
    migrations = [
        path for directory in (Path("migrations"), Path("alembic")) if directory.exists()
        for path in directory.rglob("*v22_4*")
    ]
    assert "delivery success or failure metadata" in note
    assert "recipient acknowledgement separately" in note
    assert "outstanding acknowledgement" in note
    assert "original dispatch record unchanged" in note
    assert "record-delivery-receipt" in script
    assert "record-recipient-acknowledgement" in script
    assert migrations == []
