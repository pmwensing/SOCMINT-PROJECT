from pathlib import Path

from src.socmint import database
from src.socmint.case_intelligence_review_routes_v18 import (
    register_case_intelligence_review_routes_v18,
)
from src.socmint.case_intelligence_review_workspace_v18 import (
    record_case_review_decision,
)
from src.socmint.dashboard import create_app
from src.socmint.persistent_case_review_decisions_v19_0 import (
    persist_case_review_decision,
)
from src.socmint.persistent_decision_supervisor_queue_v19_3 import (
    assign_persistent_decision_reviewer,
)
from src.socmint.reviewer_work_queue_v19_5 import (
    REVIEWER_WORK_QUEUE_SCHEMA,
    build_reviewer_work_queue,
    update_assigned_decision_review_state,
)


def _configure(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'app.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    database.configure_database(url)


def _app(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    app = create_app()
    register_case_intelligence_review_routes_v18(app)
    return app


def _assigned(case_id="case-alpha", reviewer="reviewer-a"):
    source = record_case_review_decision(
        case_id,
        {"decision": "needs_follow_up", "note": "source"},
        operator="analyst",
    )
    persisted = persist_case_review_decision(case_id, source, actor="analyst")
    assign_persistent_decision_reviewer(
        case_id,
        persisted["decision_record_id"],
        reviewer,
        actor="supervisor",
        note="review this case",
    )
    return persisted["decision_record_id"]


def test_v19_5_builds_current_reviewer_queue(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    record_id = _assigned()
    _assigned("case-beta", "reviewer-b")

    result = build_reviewer_work_queue("reviewer-a")

    assert result["schema"] == REVIEWER_WORK_QUEUE_SCHEMA
    assert result["entry_count"] == 1
    assert result["entries"][0]["decision_record_id"] == record_id
    assert result["entries"][0]["case_id"] == "case-alpha"
    assert result["entries"][0]["assignment_note"] == "review this case"
    assert (
        result["entries"][0]["case_workspace_href"]
        == "/case-intelligence-review/case-alpha"
    )


def test_v19_5_updates_only_assigned_reviewer_decision(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    record_id = _assigned()

    allowed = update_assigned_decision_review_state(
        "case-alpha",
        record_id,
        "reviewed",
        reviewer="reviewer-a",
        note="completed review",
    )
    blocked = update_assigned_decision_review_state(
        "case-alpha",
        record_id,
        "accepted",
        reviewer="reviewer-b",
    )

    assert allowed["status"] == "recorded"
    assert allowed["review_state"] == "reviewed"
    assert allowed["original_decision_mutated"] is False
    assert blocked["blockers"][0]["key"] == "decision_not_assigned_to_reviewer"


def test_v19_5_routes_and_ui(tmp_path, monkeypatch):
    client = _app(tmp_path, monkeypatch).test_client()
    record_id = _assigned()
    with client.session_transaction() as sess:
        sess["user"] = "reviewer-a"
        sess["_csrf_token"] = "test-csrf"

    api = client.get("/api/v1/case-intelligence-review/my-assignments")
    ui = client.get("/case-intelligence-review/my-assignments")
    update = client.post(
        f"/api/v1/case-intelligence-review/my-assignments/case-alpha/decisions/{record_id}/review-state",
        json={"review_state": "accepted", "note": "verified"},
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert api.status_code == 200
    assert api.get_json()["entry_count"] == 1
    assert ui.status_code == 200
    assert b"Reviewer Work Queue / My Assignments" in ui.data
    assert b"Open case workspace" in ui.data
    assert b"review this case" in ui.data
    assert update.status_code == 200
    assert update.get_json()["review_state"] == "accepted"


def test_v19_5_login_ui_script_release_note_and_no_migration(tmp_path, monkeypatch):
    client = _app(tmp_path, monkeypatch).test_client()
    assert (
        client.get("/api/v1/case-intelligence-review/my-assignments").status_code == 401
    )
    assert client.get("/case-intelligence-review/my-assignments").status_code == 302

    script = Path("src/socmint/static/reviewer_work_queue_v19_5.js").read_text(
        encoding="utf-8"
    )
    note = Path("release/V19_5_REVIEWER_WORK_QUEUE_MY_ASSIGNMENTS.md").read_text(
        encoding="utf-8"
    )
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v19_5*")
    ]
    assert "saveReviewState" in script
    assert "my-assignments" in script
    assert "focused queue" in note
    assert "source decision" in note
    assert migrations == []
