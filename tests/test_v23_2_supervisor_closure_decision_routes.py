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


def test_v23_2_route_and_ui(tmp_path, monkeypatch):
    from src.socmint import case_closure_routes_v23_0 as routes

    monkeypatch.setattr(
        routes, "build_case_closure_workspace", lambda case_id: _workspace()
    )
    monkeypatch.setattr(
        routes,
        "latest_closure_readiness_review",
        lambda case_id: {
            "decision": "ready",
            "reviewed_by": "reviewer",
            "reviewed_at": "2026-06-14T21:10:00",
            "review_id": "closure-readiness-1",
        },
    )
    monkeypatch.setattr(
        routes,
        "latest_supervisor_closure_decision",
        lambda case_id: {
            "decision": "close",
            "decided_by": "supervisor",
            "decided_at": "2026-06-14T21:20:00",
            "closure_decision_id": "closure-decision-1",
        },
    )
    monkeypatch.setattr(
        routes,
        "record_supervisor_closure_decision",
        lambda *a, **k: {
            "status": "closure_decision_recorded",
            "decision_record_id": 82,
            "decision": "close",
            "case_closed": True,
        },
    )

    client = _app(tmp_path, monkeypatch).test_client()
    with client.session_transaction() as sess:
        sess["_csrf_token"] = "test-csrf"
    unauthenticated = client.post(
        "/api/v1/case-closure/case-alpha/closure-decision",
        json={},
        headers={"X-CSRF-Token": "test-csrf"},
    )
    assert unauthenticated.status_code == 401

    with client.session_transaction() as sess:
        sess["user"] = "supervisor"
        sess["_csrf_token"] = "test-csrf"

    ui = client.get("/case-closure/case-alpha")
    response = client.post(
        "/api/v1/case-closure/case-alpha/closure-decision",
        json={"decision": "close", "confirmed": True, "note": "Close case."},
        headers={"X-CSRF-Token": "test-csrf"},
    )
    assert ui.status_code == 200
    assert b"Supervisor Closure Decision" in ui.data
    assert b"record-supervisor-closure-decision" in ui.data
    assert b"closure-decision-1" in ui.data
    assert b"does not assign retention or generate an archive package" in ui.data
    assert response.status_code == 200
    assert response.get_json()["decision_record_id"] == 82


def test_v23_2_release_note_client_and_no_migration():
    note = Path("release/V23_2_SUPERVISOR_CLOSURE_DECISION.md").read_text(
        encoding="utf-8"
    )
    script = Path("src/socmint/static/case_closure_workspace_v23_0.js").read_text(
        encoding="utf-8"
    )
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v23_2*")
    ]
    assert "latest readiness review" in note
    assert "close, hold, or return" in note
    assert "readiness-review ID and hash" in note
    assert "without assigning retention or generating the archive package" in note
    assert "closure-decision" in script
    assert "record-supervisor-closure-decision" in script
    assert migrations == []
