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
        "retention_policies": [{
            "policy_id": "standard_case_retention",
            "display_name": "Standard case retention",
            "retention_years": 7,
            "archive_class": "standard",
            "description": "Seven-year retention.",
        }],
        "proposed_retention_policy": {
            "policy_id": "standard_case_retention",
            "display_name": "Standard case retention",
            "retention_years": 7,
            "archive_class": "standard",
            "description": "Seven-year retention.",
        },
        "supervisor_actions": [],
        "links": {
            "release_workspace": "/dossier-release/case-alpha",
            "release_history": "/dossier-release/case-alpha/history",
            "case_delivery_workspace": "/case-delivery?case_id=case-alpha",
        },
    }


def test_v23_3_route_and_ui(tmp_path, monkeypatch):
    from src.socmint import case_closure_routes_v23_0 as routes

    monkeypatch.setattr(routes, "build_case_closure_workspace", lambda case_id: _workspace())
    monkeypatch.setattr(routes, "latest_closure_readiness_review", lambda case_id: {
        "decision": "ready",
        "reviewed_by": "reviewer",
        "reviewed_at": "2026-06-14T21:10:00",
        "review_id": "closure-readiness-1",
    })
    monkeypatch.setattr(routes, "latest_supervisor_closure_decision", lambda case_id: {
        "decision": "close",
        "case_closed": True,
        "decided_by": "supervisor",
        "decided_at": "2026-06-14T21:20:00",
        "closure_decision_id": "closure-decision-1",
    })
    monkeypatch.setattr(routes, "latest_retention_assignment", lambda case_id: {
        "policy": {"display_name": "Standard case retention"},
        "disposition": {
            "disposition": "retain_until_expiration",
            "retention_expires_at": "2033-06-14T21:20:00",
        },
        "assigned_by": "records-supervisor",
        "assigned_at": "2026-06-14T21:30:00",
        "retention_assignment_id": "retention-assignment-1",
    })
    monkeypatch.setattr(routes, "assign_retention_policy", lambda *a, **k: {
        "status": "retention_assignment_recorded",
        "assignment_record_id": 83,
        "retention_assignment_id": "retention-assignment-1",
    })

    client = _app(tmp_path, monkeypatch).test_client()
    with client.session_transaction() as sess:
        sess["_csrf_token"] = "test-csrf"
    unauthenticated = client.post(
        "/api/v1/case-closure/case-alpha/retention-assignment",
        json={},
        headers={"X-CSRF-Token": "test-csrf"},
    )
    assert unauthenticated.status_code == 401

    with client.session_transaction() as sess:
        sess["user"] = "records-supervisor"
        sess["_csrf_token"] = "test-csrf"

    ui = client.get("/case-closure/case-alpha")
    response = client.post(
        "/api/v1/case-closure/case-alpha/retention-assignment",
        json={
            "policy_id": "standard_case_retention",
            "confirmed": True,
            "note": "Assign standard retention.",
        },
        headers={"X-CSRF-Token": "test-csrf"},
    )
    assert ui.status_code == 200
    assert b"Retention Policy Assignment" in ui.data
    assert b"record-retention-assignment" in ui.data
    assert b"retention-assignment-1" in ui.data
    assert b"does not generate the archive package" in ui.data
    assert response.status_code == 200
    assert response.get_json()["assignment_record_id"] == 83


def test_v23_3_release_note_client_and_no_migration():
    note = Path("release/V23_3_RETENTION_POLICY_ASSIGNMENT.md").read_text(encoding="utf-8")
    script = Path("src/socmint/static/case_closure_workspace_v23_0.js").read_text(encoding="utf-8")
    migrations = [
        path for directory in (Path("migrations"), Path("alembic")) if directory.exists()
        for path in directory.rglob("*v23_3*")
    ]
    assert "latest supervisor decision to be close" in note
    assert "retention catalog" in note
    assert "retention disposition" in note
    assert "without generating the archive package" in note
    assert "retention-assignment" in script
    assert "record-retention-assignment" in script
    assert migrations == []
