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
        "schema": "socmint.collaboration_notes_mentions.v26_2",
        "version": "v26.2.0",
        "status": "attention_required",
        "case_id": "case-a",
        "user_identity": "alice",
        "target_types": [
            "case",
            "evidence",
            "review",
            "closure",
            "archive",
            "release",
            "confirmed_link",
            "relationship_graph",
        ],
        "visibility_scopes": ["case_team", "supervisors", "private"],
        "priorities": ["low", "normal", "high", "urgent"],
        "notes": [
            {
                "collaboration_note_id": "note-1",
                "collaboration_note_sha256": "n" * 64,
                "recorded_at": "2026-06-16T14:00:00+00:00",
                "author": "paul",
                "target_type": "case",
                "target_id": None,
                "priority": "high",
                "visibility": "case_team",
                "mentioned_users": ["alice"],
                "note_status": "active",
                "body": "Review this case.",
                "acknowledgement_required": True,
            }
        ],
        "active_notes": [],
        "active_note_count": 1,
        "unread_mentions": [{"collaboration_note_id": "note-1"}],
        "unread_mention_count": 1,
        "acknowledgement_required": [{"collaboration_note_id": "note-1"}],
        "acknowledgement_required_count": 1,
        "history": [],
        "history_count": 1,
        "read_only_view_created_record": False,
        "source_records_mutated": False,
        "case_access_scope_changed": False,
        "access_granted_by_mention": False,
        "next_action": "manage_collaboration_notes",
    }


def test_v26_2_routes_require_login_enforce_scope_and_render(tmp_path, monkeypatch):
    from src.socmint import collaboration_notes_routes_v26_2 as routes

    monkeypatch.setattr(
        routes,
        "build_collaboration_notes_workspace",
        lambda case_id, user_identity=None: _workspace(),
    )
    monkeypatch.setattr(
        routes,
        "find_note",
        lambda case_id, note_id: {
            "collaboration_note_id": note_id,
            "collaboration_note_sha256": "n" * 64,
            "note_status": "active",
        },
    )
    monkeypatch.setattr(
        routes,
        "create_note",
        lambda case_id, **kwargs: {
            "status": "collaboration_note_recorded",
            "case_id": case_id,
            "recorded_by": kwargs["author"],
        },
    )
    monkeypatch.setattr(
        routes,
        "correct_note",
        lambda case_id, note_id, **kwargs: {
            "status": "collaboration_note_correction_recorded",
            "case_id": case_id,
            "supersedes_note_id": note_id,
        },
    )
    monkeypatch.setattr(
        routes,
        "acknowledge_note",
        lambda case_id, note_id, **kwargs: {
            "status": "collaboration_note_acknowledged",
            "case_id": case_id,
            "collaboration_note_id": note_id,
        },
    )
    monkeypatch.setattr(
        routes,
        "mark_note_read",
        lambda case_id, note_id, **kwargs: {
            "status": "collaboration_note_marked_read",
            "case_id": case_id,
            "collaboration_note_id": note_id,
        },
    )

    client = _app(tmp_path, monkeypatch).test_client()
    assert client.get("/api/v1/cases/case-a/collaboration-notes").status_code == 401
    assert client.get("/cases/case-a/collaboration-notes").status_code in {302, 303}

    with client.session_transaction() as sess:
        sess["user"] = "alice"
        sess["allowed_case_ids"] = ["case-a"]
        sess["_csrf_token"] = "csrf-v26-2"

    assert (
        client.get("/api/v1/cases/case-hidden/collaboration-notes").status_code == 403
    )
    ui = client.get("/cases/case-a/collaboration-notes")
    api = client.get("/api/v1/cases/case-a/collaboration-notes")
    note = client.post(
        "/api/v1/cases/case-a/collaboration-notes",
        json={
            "body": "x",
            "target_type": "case",
            "mentioned_users": ["bob"],
            "confirmed": True,
        },
        headers={"X-CSRF-Token": "csrf-v26-2"},
    )
    correction = client.post(
        "/api/v1/cases/case-a/collaboration-notes/note-1/correct",
        json={"body": "fixed", "reason": "clarified", "confirmed": True},
        headers={"X-CSRF-Token": "csrf-v26-2"},
    )
    ack = client.post(
        "/api/v1/cases/case-a/collaboration-notes/note-1/acknowledge",
        json={"response": "ok", "confirmed": True},
        headers={"X-CSRF-Token": "csrf-v26-2"},
    )
    read = client.post(
        "/api/v1/cases/case-a/collaboration-notes/note-1/read",
        json={},
        headers={"X-CSRF-Token": "csrf-v26-2"},
    )

    assert ui.status_code == 200
    assert b"Collaboration Notes and Mentions" in ui.data
    assert b"Create Note" in ui.data
    assert b"Current Notes" in ui.data
    assert b"Unread Mentions" in ui.data
    assert b"Acknowledgement Required" in ui.data
    assert b"Corrections supersede rather than replace prior notes" in ui.data
    assert api.status_code == 200
    assert api.get_json()["unread_mention_count"] == 1
    assert note.status_code == 200 and note.get_json()["recorded_by"] == "alice"
    assert correction.status_code == 200
    assert ack.status_code == 200
    assert read.status_code == 200


def test_v26_2_release_note_client_and_no_migration():
    note = Path("release/V26_2_COLLABORATION_NOTES_MENTIONS.md").read_text(
        encoding="utf-8"
    )
    client = Path("src/socmint/static/collaboration_notes_mentions_v26_2.js").read_text(
        encoding="utf-8"
    )
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v26_2*")
    ]
    for phrase in (
        "case-level note",
        "evidence-specific note",
        "review-specific note",
        "closure and archive",
        "mentions",
        "visibility",
        "priority",
        "acknowledgement",
        "superseding note",
        "mention never grants access",
        "append-only",
    ):
        assert phrase in note
    assert "record-collaboration-note" in client
    assert "correct-note" in client
    assert "ack-note" in client
    assert "read-note" in client
    assert migrations == []
