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
        "schema": "socmint.collaboration_responses_resolution.v26_4",
        "version": "v26.4.0",
        "status": "attention_required",
        "case_id": "case-a",
        "response_types": ["acknowledgement", "acceptance", "decline", "response_note", "completion", "escalation", "resolution"],
        "target_types": ["note", "request", "handoff"],
        "latest_responses": [{"target_type": "request", "target_id": "request-1", "response_type": "acceptance"}],
        "unresolved_responses": [{"target_type": "request", "target_id": "request-1", "response_type": "acceptance"}],
        "counts": {"history": 1, "targets": 1, "unresolved": 1, "resolved": 0},
        "history": [],
        "source_records_mutated": False,
        "read_only_view_created_record": False,
        "case_access_scope_changed": False,
        "next_action": "manage_collaboration_responses",
    }


def test_v26_4_routes_require_login_enforce_scope_and_render(tmp_path, monkeypatch):
    from src.socmint import collaboration_responses_resolution_routes_v26_4 as routes

    monkeypatch.setattr(routes, "build_collaboration_response_workspace", lambda case_id: _workspace())
    monkeypatch.setattr(routes, "record_collaboration_response", lambda case_id, **kwargs: {
        "status": "collaboration_response_recorded",
        "case_id": case_id,
        "target_type": kwargs["target_type"],
        "target_id": kwargs["target_id"],
        "response_type": kwargs["response_type"],
        "recorded_by": kwargs["responding_user"],
    })

    client = _app(tmp_path, monkeypatch).test_client()
    assert client.get("/api/v1/cases/case-a/collaboration-responses").status_code == 401
    assert client.get("/cases/case-a/collaboration-responses").status_code in {302, 303}

    with client.session_transaction() as sess:
        sess["user"] = "alice"
        sess["allowed_case_ids"] = ["case-a"]
        sess["_csrf_token"] = "csrf-v26-4"

    assert client.get("/api/v1/cases/hidden/collaboration-responses").status_code == 403
    assert client.post(
        "/api/v1/cases/hidden/collaboration-responses",
        json={"confirmed": True},
        headers={"X-CSRF-Token": "csrf-v26-4"},
    ).status_code == 403

    ui = client.get("/cases/case-a/collaboration-responses")
    api = client.get("/api/v1/cases/case-a/collaboration-responses")
    response = client.post(
        "/api/v1/cases/case-a/collaboration-responses",
        json={
            "target_type": "request",
            "target_id": "request-1",
            "response_type": "acceptance",
            "reason": "I will handle this request.",
            "confirmed": True,
        },
        headers={"X-CSRF-Token": "csrf-v26-4"},
    )

    assert ui.status_code == 200
    assert b"Acknowledgements, Responses, and Resolution" in ui.data
    assert b"Record Response" in ui.data
    assert b"Latest Response State" in ui.data
    assert b"Unresolved Responses" in ui.data
    assert b"Acknowledgement does not equal completion" in ui.data
    assert api.status_code == 200
    assert api.get_json()["counts"]["unresolved"] == 1
    assert response.status_code == 200
    assert response.get_json()["recorded_by"] == "alice"
    assert response.get_json()["response_type"] == "acceptance"


def test_v26_4_release_note_client_and_no_migration():
    note = Path("release/V26_4_ACKNOWLEDGEMENTS_RESPONSES_RESOLUTION.md").read_text(encoding="utf-8")
    script = Path("src/socmint/static/collaboration_responses_resolution_v26_4.js").read_text(encoding="utf-8")
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v26_4*")
    ]
    for phrase in (
        "acknowledgement",
        "acceptance",
        "decline",
        "response note",
        "completion",
        "escalation",
        "resolution",
        "original item ID and SHA-256",
        "current case state",
        "append-only",
        "does not equal completion",
    ):
        assert phrase in note
    assert "v26-4-record-response" in script
    assert migrations == []
