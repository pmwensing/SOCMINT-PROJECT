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


def test_v22_5_routes_and_ui(tmp_path, monkeypatch):
    from src.socmint import dossier_release_workspace_routes_v22_0 as routes

    monkeypatch.setattr(
        routes, "build_dossier_release_workspace", lambda *a, **k: _workspace()
    )
    monkeypatch.setattr(routes, "latest_release_authorization", lambda case_id: None)
    monkeypatch.setattr(
        routes,
        "build_release_package_preview",
        lambda case_id: {
            "section_count": 0,
            "attachment_count": 0,
            "restricted_section_count": 0,
            "blocker_count": 0,
            "blockers": [],
            "included_sections": [],
            "included_attachments": [],
        },
    )
    monkeypatch.setattr(routes, "latest_release_preview", lambda case_id: None)
    monkeypatch.setattr(
        routes,
        "build_secure_distribution_readiness",
        lambda case_id: {
            "status": "ready_for_final_confirmation",
            "ready": True,
            "blocker_count": 0,
            "blockers": [],
            "latest_distribution": None,
        },
    )
    monkeypatch.setattr(
        routes,
        "build_delivery_receipt_state",
        lambda case_id: {
            "status": "tracking",
            "delivery_succeeded": False,
            "acknowledgement_received": False,
            "acknowledgement_outstanding": False,
            "next_action": "review_delivery_failure",
            "latest_delivery_receipt": None,
            "latest_recipient_acknowledgement": None,
        },
    )
    monkeypatch.setattr(
        routes,
        "build_delivery_recovery_state",
        lambda case_id: {
            "status": "tracking",
            "delivery_failed": True,
            "failed_delivery_review_required": True,
            "recall_available": True,
            "reissue_available": True,
            "next_action": "review_failed_delivery",
        },
    )
    monkeypatch.setattr(
        routes,
        "review_failed_delivery",
        lambda *a, **k: {
            "status": "failed_delivery_review_recorded",
            "record_id": 71,
        },
    )
    monkeypatch.setattr(
        routes,
        "request_recall",
        lambda *a, **k: {
            "status": "recall_requested",
            "record_id": 72,
        },
    )
    monkeypatch.setattr(
        routes,
        "authorize_reissue",
        lambda *a, **k: {
            "status": "reissue_authorized",
            "record_id": 73,
        },
    )

    client = _app(tmp_path, monkeypatch).test_client()
    assert (
        client.get("/api/v1/dossier-release/case-alpha/delivery-recovery").status_code
        == 401
    )
    with client.session_transaction() as sess:
        sess["user"] = "operator"
        sess["_csrf_token"] = "test-csrf"

    ui = client.get("/dossier-release/case-alpha")
    state = client.get("/api/v1/dossier-release/case-alpha/delivery-recovery")
    review = client.post(
        "/api/v1/dossier-release/case-alpha/failed-delivery-review",
        json={"confirmed": True, "root_cause": "failed", "resolution_plan": "retry"},
        headers={"X-CSRF-Token": "test-csrf"},
    )
    recall = client.post(
        "/api/v1/dossier-release/case-alpha/recall",
        json={"confirmed": True, "reason": "withdraw"},
        headers={"X-CSRF-Token": "test-csrf"},
    )
    reissue = client.post(
        "/api/v1/dossier-release/case-alpha/reissue-authorization",
        json={
            "confirmed": True,
            "target_recipient_id": "recipient-2",
            "target_delivery_channel": "encrypted_email",
            "reason": "retry",
        },
        headers={"X-CSRF-Token": "test-csrf"},
    )
    assert ui.status_code == 200
    assert b"Failed Delivery, Recall, and Reissue Controls" in ui.data
    assert (
        b"original dispatch, receipt, and acknowledgement events remain unchanged"
        in ui.data
    )
    assert state.status_code == 200
    assert state.get_json()["reissue_available"] is True
    assert review.status_code == 200 and review.get_json()["record_id"] == 71
    assert recall.status_code == 200 and recall.get_json()["record_id"] == 72
    assert reissue.status_code == 200 and reissue.get_json()["record_id"] == 73


def test_v22_5_release_note_client_and_no_migration():
    note = Path("release/V22_5_FAILED_DELIVERY_RECALL_REISSUE_CONTROLS.md").read_text(
        encoding="utf-8"
    )
    script = Path("src/socmint/static/dossier_release_workspace_v22_0.js").read_text(
        encoding="utf-8"
    )
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v22_5*")
    ]
    assert "failed-delivery review" in note
    assert "explicit recall requests" in note
    assert (
        "reissue authorization tied to the original package and recipient history"
        in note
    )
    assert (
        "without altering the original dispatch, receipt, or acknowledgement events"
        in note
    )
    assert "record-failed-delivery-review" in script
    assert "request-delivery-recall" in script
    assert "authorize-delivery-reissue" in script
    assert migrations == []
