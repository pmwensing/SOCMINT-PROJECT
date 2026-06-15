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
        "status": "eligible_for_closure_review",
        "current_release_outcome": "delivered_and_acknowledged",
        "closure_eligible": True,
        "archive_ready": True,
        "blocker_count": 0,
        "blockers": [],
        "release_history": {"closure_summary": {"case_id": "case-alpha", "closure_ready": True}},
        "delivery_recovery_state": {
            "delivery_failed": False,
            "delivery_succeeded": True,
            "acknowledgement_received": True,
            "next_action": "monitor_delivery_recovery",
        },
        "retention_policies": [],
        "proposed_retention_policy": None,
        "supervisor_actions": [],
        "links": {
            "release_workspace": "/dossier-release/case-alpha",
            "release_history": "/dossier-release/case-alpha/history",
            "case_delivery_workspace": "/case-delivery?case_id=case-alpha",
        },
    }


def test_v23_5_routes_and_ui(tmp_path, monkeypatch):
    from src.socmint import case_closure_routes_v23_0 as closure_routes
    from src.socmint import case_reopen_routes_v23_5 as reopen_routes

    monkeypatch.setattr(closure_routes, "build_case_closure_workspace", lambda case_id: _workspace())
    monkeypatch.setattr(closure_routes, "latest_closure_readiness_review", lambda case_id: {"decision": "ready", "review_id": "review-1"})
    monkeypatch.setattr(closure_routes, "latest_supervisor_closure_decision", lambda case_id: {"decision": "close", "closure_decision_id": "decision-1"})
    monkeypatch.setattr(closure_routes, "latest_retention_assignment", lambda case_id: {"ready_for_archive_package": True, "retention_assignment_id": "retention-1"})
    monkeypatch.setattr(closure_routes, "latest_case_archive_package", lambda case_id: {"archive_package_id": "archive-1", "archive_package_sha256": "archive-hash", "components": {"audit_references": []}})
    monkeypatch.setattr(reopen_routes, "create_reopen_request", lambda *a, **k: {
        "status": "reopen_request_recorded",
        "request_record_id": 85,
        "reopen_request_id": "reopen-request-1",
        "case_reopened": False,
    })
    monkeypatch.setattr(reopen_routes, "authorize_reopen_request", lambda *a, **k: {
        "status": "reopen_authorization_recorded",
        "authorization_record_id": 86,
        "decision": "authorize",
        "case_reopened": True,
    })

    client = _app(tmp_path, monkeypatch).test_client()
    with client.session_transaction() as sess:
        sess["_csrf_token"] = "test-csrf"

    unauth_request = client.post(
        "/api/v1/case-closure/case-alpha/reopen-request",
        json={},
        headers={"X-CSRF-Token": "test-csrf"},
    )
    unauth_auth = client.post(
        "/api/v1/case-closure/case-alpha/reopen-authorization",
        json={},
        headers={"X-CSRF-Token": "test-csrf"},
    )
    assert unauth_request.status_code == 401
    assert unauth_auth.status_code == 401

    with client.session_transaction() as sess:
        sess["user"] = "supervisor"
        sess["_csrf_token"] = "test-csrf"

    ui = client.get("/case-closure/case-alpha")
    request_response = client.post(
        "/api/v1/case-closure/case-alpha/reopen-request",
        json={"reason": "New evidence", "confirmed": True, "note": "Review again."},
        headers={"X-CSRF-Token": "test-csrf"},
    )
    auth_response = client.post(
        "/api/v1/case-closure/case-alpha/reopen-authorization",
        json={"decision": "authorize", "confirmed": True, "note": "Approved."},
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert ui.status_code == 200
    assert b"Reopen Request and Authorization" in ui.data
    assert b"record-reopen-request" in ui.data
    assert b"record-reopen-authorization" in ui.data
    assert b"closed case and archive remain unchanged unless reopening is authorized" in ui.data
    assert request_response.status_code == 200
    assert request_response.get_json()["request_record_id"] == 85
    assert auth_response.status_code == 200
    assert auth_response.get_json()["authorization_record_id"] == 86


def test_v23_5_release_note_client_and_no_migration():
    note = Path("release/V23_5_REOPEN_REQUEST_AUTHORIZATION.md").read_text(encoding="utf-8")
    script = Path("src/socmint/static/case_closure_workspace_v23_0.js").read_text(encoding="utf-8")
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v23_5*")
    ]
    assert "existing archive package" in note
    assert "separate reopen request" in note
    assert "supervisor authorization or denial" in note
    assert "archive package ID and hash" in note
    assert "closed case and archive records unchanged" in note
    assert "reopen-request" in script
    assert "reopen-authorization" in script
    assert migrations == []
