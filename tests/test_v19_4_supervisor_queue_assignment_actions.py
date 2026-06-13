from __future__ import annotations

import json
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
    AUDIT_ACTION,
    persist_case_review_decision,
    set_persistent_decision_review_state,
)
from src.socmint.persistent_decision_supervisor_queue_v19_3 import (
    ASSIGNMENT_ACTION,
    assign_persistent_decision_reviewer,
    build_persistent_decision_supervisor_queue,
)


def _configure(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'app.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    database.configure_database(database_url)


def _app(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    app = create_app()
    register_case_intelligence_review_routes_v18(app)
    return app


def _seed(case_id="case-alpha", decision="approve_review"):
    source = record_case_review_decision(
        case_id,
        {"decision": decision, "note": "source note"},
        operator="analyst",
        recorded_at="2026-06-13T16:30:00+00:00",
    )
    return persist_case_review_decision(case_id, source, actor="analyst")


def test_v19_4_assigns_and_reassigns_with_immutable_annotations(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    persisted = _seed()
    record_id = persisted["decision_record_id"]

    session = database.Session()
    try:
        source_before = session.query(database.AuditLog).filter_by(id=record_id).one()
        original_details = source_before.details
    finally:
        session.close()

    first = assign_persistent_decision_reviewer(
        "case-alpha",
        record_id,
        "reviewer-a",
        actor="supervisor",
        note="initial assignment",
    )
    second = assign_persistent_decision_reviewer(
        "case-alpha",
        record_id,
        "reviewer-b",
        actor="supervisor",
        note="reassigned for coverage",
    )

    assert first["status"] == "recorded"
    assert second["status"] == "recorded"
    assert second["assigned_reviewer"] == "reviewer-b"
    assert second["original_decision_mutated"] is False

    session = database.Session()
    try:
        source_after = session.query(database.AuditLog).filter_by(id=record_id).one()
        assignments = (
            session.query(database.AuditLog)
            .filter_by(action=ASSIGNMENT_ACTION, target_value="case-alpha")
            .all()
        )
        assert source_after.action == AUDIT_ACTION
        assert source_after.details == original_details
        assert len(assignments) == 2
        assert json.loads(assignments[-1].details)["assigned_reviewer"] == "reviewer-b"
    finally:
        session.close()

    queue = build_persistent_decision_supervisor_queue()
    entry = queue["entries"][0]
    assert entry["assigned_reviewer"] == "reviewer-b"
    assert entry["assigned_by"] == "supervisor"
    assert entry["assignment_note"] == "reassigned for coverage"


def test_v19_4_blocks_missing_reviewer_wrong_case_and_completed_decision(
    tmp_path, monkeypatch
):
    _configure(tmp_path, monkeypatch)
    persisted = _seed()
    record_id = persisted["decision_record_id"]

    missing = assign_persistent_decision_reviewer(
        "case-alpha", record_id, "", actor="supervisor"
    )
    wrong_case = assign_persistent_decision_reviewer(
        "case-other", record_id, "reviewer", actor="supervisor"
    )
    set_persistent_decision_review_state(
        "case-alpha", record_id, "accepted", actor="supervisor"
    )
    completed = assign_persistent_decision_reviewer(
        "case-alpha", record_id, "reviewer", actor="supervisor"
    )

    assert missing["blockers"][0]["key"] == "assigned_reviewer_required"
    assert wrong_case["blockers"][0]["key"] == "decision_record_not_found"
    assert completed["blockers"][0]["key"] == "decision_not_outstanding"


def test_v19_4_assignment_route_requires_login(tmp_path, monkeypatch):
    client = _app(tmp_path, monkeypatch).test_client()
    with client.session_transaction() as sess:
        sess["_csrf_token"] = "test-csrf"
    response = client.post(
        "/api/v1/case-intelligence-review/supervisor-queue/case-alpha/"
        "decisions/1/assignment",
        json={"assigned_reviewer": "reviewer"},
        headers={"X-CSRF-Token": "test-csrf"},
    )
    assert response.status_code == 401


def test_v19_4_assignment_route_returns_refreshed_queue(tmp_path, monkeypatch):
    client = _app(tmp_path, monkeypatch).test_client()
    with client.session_transaction() as sess:
        sess["user"] = "supervisor"
        sess["_csrf_token"] = "test-csrf"

    decision = client.post(
        "/api/v1/case-intelligence-review/case-alpha/decisions",
        json={"decision": "needs_follow_up", "note": "review"},
        headers={"X-CSRF-Token": "test-csrf"},
    ).get_json()["persistent_decision"]

    response = client.post(
        "/api/v1/case-intelligence-review/supervisor-queue/case-alpha/"
        f"decisions/{decision['decision_record_id']}/assignment",
        json={"assigned_reviewer": "reviewer-a", "note": "take ownership"},
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["assigned_reviewer"] == "reviewer-a"
    assert payload["assigned_by"] == "supervisor"
    assert payload["supervisor_queue"]["entries"][0]["assigned_reviewer"] == (
        "reviewer-a"
    )


def test_v19_4_ui_script_release_note_and_no_migration(tmp_path, monkeypatch):
    client = _app(tmp_path, monkeypatch).test_client()
    with client.session_transaction() as sess:
        sess["user"] = "supervisor"
        sess["_csrf_token"] = "test-csrf"
    client.post(
        "/api/v1/case-intelligence-review/case-alpha/decisions",
        json={"decision": "approve_review", "note": "ready"},
        headers={"X-CSRF-Token": "test-csrf"},
    )

    response = client.get("/case-intelligence-review/supervisor-queue")
    script = Path(
        "src/socmint/static/persistent_decision_supervisor_queue_v19_4.js"
    ).read_text(encoding="utf-8")
    note = Path("release/V19_4_SUPERVISOR_QUEUE_ASSIGNMENT_ACTIONS.md").read_text(
        encoding="utf-8"
    )
    migration_matches = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v19_4*")
    ]

    assert response.status_code == 200
    assert b"assignment-reviewer" in response.data
    assert b"save-supervisor-assignment" in response.data
    assert b"immutable audit annotations" in response.data
    assert "saveAssignment" in script
    assert "/assignment" in script
    assert "assign or reassign" in note
    assert "immutable audit annotation" in note
    assert migration_matches == []
