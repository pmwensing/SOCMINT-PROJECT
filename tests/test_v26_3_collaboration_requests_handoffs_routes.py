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


def test_v26_3_routes_and_ui(tmp_path, monkeypatch):
    from src.socmint import collaboration_requests_handoffs_routes_v26_3 as routes

    workspace = {
        "schema": "socmint.collaboration_requests_handoffs.v26_3",
        "version": "v26.3.0",
        "status": "attention_required",
        "case_id": "case-a",
        "request_types": ["evidence_review"],
        "handoff_types": ["review_task"],
        "priorities": ["normal"],
        "requests": [],
        "handoffs": [],
        "pending_requests": [{"collaboration_request_id": "r1"}],
        "pending_handoffs": [{"collaboration_handoff_id": "h1"}],
        "counts": {
            "requests": 1,
            "handoffs": 1,
            "pending_requests": 1,
            "pending_handoffs": 1,
        },
        "history": [],
        "source_records_mutated": False,
        "read_only_view_created_record": False,
        "case_access_scope_changed": False,
        "next_action": "manage_review_requests_and_handoffs",
    }
    monkeypatch.setattr(routes, "build_workspace", lambda case_id: workspace)
    monkeypatch.setattr(
        routes,
        "create_request",
        lambda case_id, **kwargs: {
            "status": "collaboration_request_recorded",
            "recorded_by": kwargs["actor"],
        },
    )
    monkeypatch.setattr(
        routes,
        "create_handoff",
        lambda case_id, **kwargs: {
            "status": "collaboration_handoff_recorded",
            "recorded_by": kwargs["actor"],
        },
    )
    monkeypatch.setattr(
        routes,
        "transition",
        lambda kind, case_id, item_id, **kwargs: {
            "status": f"collaboration_{kind}_{kwargs['decision']}",
            f"collaboration_{kind}_id": item_id,
        },
    )
    client = _app(tmp_path, monkeypatch).test_client()
    assert client.get("/api/v1/cases/case-a/collaboration-requests").status_code == 401
    with client.session_transaction() as s:
        s["user"] = "paul"
        s["allowed_case_ids"] = ["case-a"]
        s["_csrf_token"] = "csrf-v26-3"
    assert client.get("/api/v1/cases/hidden/collaboration-requests").status_code == 403
    ui = client.get("/cases/case-a/collaboration-requests")
    api = client.get("/api/v1/cases/case-a/collaboration-requests")
    req = client.post(
        "/api/v1/cases/case-a/collaboration-requests",
        json={
            "requested_from": "alice",
            "request_type": "evidence_review",
            "reason": "review",
            "confirmed": True,
        },
        headers={"X-CSRF-Token": "csrf-v26-3"},
    )
    hand = client.post(
        "/api/v1/cases/case-a/collaboration-handoffs",
        json={
            "handoff_to": "bob",
            "handoff_type": "review_task",
            "reason": "handoff",
            "confirmed": True,
        },
        headers={"X-CSRF-Token": "csrf-v26-3"},
    )
    trans = client.post(
        "/api/v1/cases/case-a/collaboration-requests/r1/accepted",
        json={"confirmed": True},
        headers={"X-CSRF-Token": "csrf-v26-3"},
    )
    assert (
        ui.status_code == 200
        and b"Review Requests and Task Handoffs" in ui.data
        and b"Pending Requests" in ui.data
    )
    assert api.status_code == 200 and api.get_json()["counts"]["pending_handoffs"] == 1
    assert (
        req.status_code == 200 and hand.status_code == 200 and trans.status_code == 200
    )


def test_v26_3_release_note_client_and_no_migration():
    note = Path("release/V26_3_REVIEW_REQUESTS_TASK_HANDOFFS.md").read_text(
        encoding="utf-8"
    )
    script = Path(
        "src/socmint/static/collaboration_requests_handoffs_v26_3.js"
    ).read_text(encoding="utf-8")
    migrations = [
        p
        for d in (Path("migrations"), Path("alembic"))
        if d.exists()
        for p in d.rglob("*v26_3*")
    ]
    for phrase in (
        "review request",
        "task handoff",
        "acknowledged",
        "accepted",
        "declined",
        "completed",
        "cancelled",
        "source bindings",
        "append-only",
        "acknowledgement does not equal completion",
    ):
        assert phrase in note
    assert "v26-3-create-request" in script and "v26-3-create-handoff" in script
    assert migrations == []
