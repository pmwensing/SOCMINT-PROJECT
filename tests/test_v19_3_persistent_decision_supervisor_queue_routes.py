from pathlib import Path

from src.socmint import database
from src.socmint.case_intelligence_review_routes_v18 import (
    register_case_intelligence_review_routes_v18,
)
from src.socmint.dashboard import create_app


def _app(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'app.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    database.configure_database(database_url)
    app = create_app()
    register_case_intelligence_review_routes_v18(app)
    return app


def test_v19_3_routes_require_login(tmp_path, monkeypatch):
    client = _app(tmp_path, monkeypatch).test_client()
    assert (
        client.get("/api/v1/case-intelligence-review/supervisor-queue").status_code
        == 401
    )
    assert client.get("/case-intelligence-review/supervisor-queue").status_code == 302


def test_v19_3_api_and_ui_render_queue(tmp_path, monkeypatch):
    client = _app(tmp_path, monkeypatch).test_client()
    with client.session_transaction() as sess:
        sess["user"] = "supervisor"
        sess["_csrf_token"] = "test-csrf"
    client.post(
        "/api/v1/case-intelligence-review/case-alpha/decisions",
        json={"decision": "approve_review", "note": "ready"},
        headers={"X-CSRF-Token": "test-csrf"},
    )

    api = client.get(
        "/api/v1/case-intelligence-review/supervisor-queue?review_state=unreviewed"
    )
    ui = client.get("/case-intelligence-review/supervisor-queue")

    assert api.status_code == 200
    assert api.get_json()["entry_count"] == 1
    assert api.get_json()["entries"][0]["case_id"] == "case-alpha"
    assert ui.status_code == 200
    assert b"Persistent Decision Supervisor Queue" in ui.data
    assert b"Oldest outstanding age" in ui.data
    assert b"Assigned reviewers" in ui.data
    assert b"Open case workspace" in ui.data


def test_v19_3_release_note_and_no_migration():
    note = Path(
        "release/V19_3_PERSISTENT_DECISION_REVIEW_SUMMARY_SUPERVISOR_QUEUE.md"
    ).read_text(encoding="utf-8")
    migration_matches = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v19_3*")
    ]
    assert "cross-case supervisor view" in note
    assert "oldest outstanding age" in note
    assert "assigned reviewer" in note
    assert migration_matches == []
