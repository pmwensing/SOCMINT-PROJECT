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
        "status": "eligible_for_closure_review",
        "current_release_outcome": "delivered_and_acknowledged",
        "closure_eligible": True,
        "archive_ready": True,
        "blocker_count": 0,
        "blockers": [],
        "release_history": {
            "closure_summary": {"case_id": "case-alpha", "closure_ready": True}
        },
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


def test_v23_4_route_and_ui(tmp_path, monkeypatch):
    from src.socmint import case_closure_routes_v23_0 as routes

    monkeypatch.setattr(
        routes, "build_case_closure_workspace", lambda case_id: _workspace()
    )
    monkeypatch.setattr(
        routes,
        "latest_closure_readiness_review",
        lambda case_id: {"decision": "ready", "review_id": "review-1"},
    )
    monkeypatch.setattr(
        routes,
        "latest_supervisor_closure_decision",
        lambda case_id: {"decision": "close", "closure_decision_id": "decision-1"},
    )
    monkeypatch.setattr(
        routes,
        "latest_retention_assignment",
        lambda case_id: {
            "ready_for_archive_package": True,
            "retention_assignment_id": "retention-1",
            "policy": {"display_name": "Standard case retention"},
            "disposition": {
                "disposition": "retain_until_expiration",
                "retention_expires_at": "2033-06-14T21:20:00",
            },
            "assigned_by": "archive-supervisor",
            "assigned_at": "2026-06-14T22:00:00",
        },
    )
    monkeypatch.setattr(
        routes,
        "latest_case_archive_package",
        lambda case_id: {
            "archive_package_id": "case-archive-1",
            "archive_package_sha256": "archive-hash",
            "generated_by": "archive-supervisor",
            "generated_at": "2026-06-14T22:10:00",
            "components": {"audit_references": [{"audit_record_id": 1}]},
        },
    )
    monkeypatch.setattr(
        routes,
        "generate_case_archive_package",
        lambda *a, **k: {
            "status": "archive_package_generated",
            "archive_record_id": 84,
            "archive_package_id": "case-archive-1",
        },
    )

    client = _app(tmp_path, monkeypatch).test_client()
    with client.session_transaction() as sess:
        sess["_csrf_token"] = "test-csrf"
    unauthenticated = client.post(
        "/api/v1/case-closure/case-alpha/archive-package",
        json={},
        headers={"X-CSRF-Token": "test-csrf"},
    )
    assert unauthenticated.status_code == 401

    with client.session_transaction() as sess:
        sess["user"] = "archive-supervisor"
        sess["_csrf_token"] = "test-csrf"

    ui = client.get("/case-closure/case-alpha")
    response = client.post(
        "/api/v1/case-closure/case-alpha/archive-package",
        json={},
        headers={"X-CSRF-Token": "test-csrf"},
    )
    assert ui.status_code == 200
    assert b"Case Archive Package" in ui.data
    assert b"generate-case-archive-package" in ui.data
    assert b"case-archive-1" in ui.data
    assert (
        b"does not change any closure, retention, dossier, release, delivery, or audit source event"
        in ui.data
    )
    assert response.status_code == 200
    assert response.get_json()["archive_record_id"] == 84


def test_v23_4_release_note_client_and_no_migration():
    note = Path("release/V23_4_CASE_ARCHIVE_PACKAGE.md").read_text(encoding="utf-8")
    script = Path("src/socmint/static/case_closure_workspace_v23_0.js").read_text(
        encoding="utf-8"
    )
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v23_4*")
    ]
    assert "latest valid retention assignment" in note
    assert (
        "closure, retention, dossier, release, delivery, and audit references" in note
    )
    assert "component hashes" in note
    assert "without changing any source event" in note
    assert "archive-package" in script
    assert "generate-case-archive-package" in script
    assert migrations == []
