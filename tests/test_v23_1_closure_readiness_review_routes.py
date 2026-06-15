from pathlib import Path

from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import register_dossier_assembly_routes_v21_0


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def _payload():
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
        "latest_readiness_review": {
            "decision": "ready",
            "reviewed_by": "supervisor",
            "reviewed_at": "2026-06-14T21:10:00",
            "review_id": "closure-readiness-1",
        },
    }


def test_v23_1_route_and_ui(tmp_path, monkeypatch):
    from src.socmint import case_closure_routes_v23_0 as routes

    monkeypatch.setattr(routes, "build_case_closure_workspace", lambda case_id: _payload())
    monkeypatch.setattr(routes, "latest_closure_readiness_review", lambda case_id: _payload()["latest_readiness_review"])
    monkeypatch.setattr(routes, "review_case_closure_readiness", lambda *a, **k: {
        "status": "review_recorded",
        "review_record_id": 81,
        "decision": "ready",
        "ready_for_supervisor_closure_decision": True,
    })

    client = _app(tmp_path, monkeypatch).test_client()
    with client.session_transaction() as sess:
        sess["_csrf_token"] = "test-csrf"
    unauthenticated = client.post(
        "/api/v1/case-closure/case-alpha/readiness-review",
        json={},
        headers={"X-CSRF-Token": "test-csrf"},
    )
    assert unauthenticated.status_code == 401

    with client.session_transaction() as sess:
        sess["user"] = "supervisor"
        sess["_csrf_token"] = "test-csrf"

    ui = client.get("/case-closure/case-alpha")
    response = client.post(
        "/api/v1/case-closure/case-alpha/readiness-review",
        json={"decision": "ready", "confirmed": True, "note": "Reviewed."},
        headers={"X-CSRF-Token": "test-csrf"},
    )
    assert ui.status_code == 200
    assert b"Closure Readiness Review" in ui.data
    assert b"record-closure-readiness-review" in ui.data
    assert b"closure-readiness-1" in ui.data
    assert b"does not close the case, assign retention, or generate an archive package" in ui.data
    assert response.status_code == 200
    assert response.get_json()["review_record_id"] == 81


def test_v23_1_release_note_client_and_no_migration():
    note = Path("release/V23_1_CLOSURE_READINESS_REVIEW.md").read_text(encoding="utf-8")
    script = Path("src/socmint/static/case_closure_workspace_v23_0.js").read_text(encoding="utf-8")
    migrations = [
        path for directory in (Path("migrations"), Path("alembic")) if directory.exists()
        for path in directory.rglob("*v23_1*")
    ]
    assert "immutable closure-readiness review" in note
    assert "source closure summary" in note
    assert "ready or not ready" in note
    assert "does not close the case" in note
    assert "readiness-review" in script
    assert "record-closure-readiness-review" in script
    assert migrations == []
