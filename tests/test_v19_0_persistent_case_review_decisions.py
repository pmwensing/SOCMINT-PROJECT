from __future__ import annotations

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
    PERSISTENT_CASE_REVIEW_DECISIONS_SCHEMA,
    list_persistent_case_review_decisions,
    persist_case_review_decision,
)


def _configure(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'app.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    database.configure_database(database_url)
    return database_url


def _app(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    app = create_app()
    register_case_intelligence_review_routes_v18(app)
    return app


def test_v19_0_persists_valid_review_decision(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    decision = record_case_review_decision(
        "case-alpha",
        {"decision": "approve_review", "note": "complete"},
        operator="analyst",
        recorded_at="2026-06-13T01:00:00+00:00",
    )

    result = persist_case_review_decision(
        "case-alpha",
        decision,
        actor="analyst",
        ip_address="127.0.0.1",
    )

    assert result["schema"] == PERSISTENT_CASE_REVIEW_DECISIONS_SCHEMA
    assert result["status"] == "persisted"
    assert result["persisted"] is True
    assert result["decision_record_id"] > 0

    history = list_persistent_case_review_decisions("case-alpha")
    assert history["entry_count"] == 1
    assert history["entries"][0]["decision"] == "approve_review"
    assert history["entries"][0]["actor"] == "analyst"
    assert history["entries"][0]["note"] == "complete"
    assert history["persistence"] == "audit_logs"


def test_v19_0_blocks_unvalidated_decision(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)

    result = persist_case_review_decision(
        "case-alpha",
        {"status": "blocked", "decision": "delete_case"},
        actor="analyst",
    )

    assert result["status"] == "blocked"
    assert result["persisted"] is False
    assert result["blockers"][0]["key"] == "decision_not_recorded"
    assert list_persistent_case_review_decisions("case-alpha")["entry_count"] == 0


def test_v19_0_persistent_history_is_case_scoped(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    first = record_case_review_decision(
        "case-one", {"decision": "needs_follow_up"}, operator="analyst"
    )
    second = record_case_review_decision(
        "case-two", {"decision": "hold_delivery"}, operator="reviewer"
    )
    persist_case_review_decision("case-one", first, actor="analyst")
    persist_case_review_decision("case-two", second, actor="reviewer")

    one = list_persistent_case_review_decisions("case-one")
    two = list_persistent_case_review_decisions("case-two")

    assert one["entry_count"] == 1
    assert one["entries"][0]["decision"] == "needs_follow_up"
    assert two["entry_count"] == 1
    assert two["entries"][0]["decision"] == "hold_delivery"


def test_v19_0_decision_route_persists_and_read_route_survives_session_clear(
    tmp_path, monkeypatch
):
    client = _app(tmp_path, monkeypatch).test_client()
    with client.session_transaction() as sess:
        sess["user"] = "analyst"
        sess["_csrf_token"] = "test-csrf"

    response = client.post(
        "/api/v1/case-intelligence-review/case-alpha/decisions",
        json={"decision": "return_to_analyst", "note": "resolve contradiction"},
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["persistent_decision"]["status"] == "persisted"

    with client.session_transaction() as sess:
        sess.clear()
        sess["user"] = "reviewer"

    history = client.get(
        "/api/v1/case-intelligence-review/case-alpha/decisions/persistent"
    )
    assert history.status_code == 200
    assert history.get_json()["entry_count"] == 1
    assert history.get_json()["entries"][0]["decision"] == "return_to_analyst"


def test_v19_0_persistent_route_requires_login(tmp_path, monkeypatch):
    client = _app(tmp_path, monkeypatch).test_client()
    response = client.get(
        "/api/v1/case-intelligence-review/case-alpha/decisions/persistent"
    )
    assert response.status_code == 401


def test_v19_0_release_note_changelog_and_no_migration():
    note = Path("release/V19_0_PERSISTENT_CASE_REVIEW_DECISIONS.md").read_text(
        encoding="utf-8"
    )
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")
    migration_matches = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v19*")
    ]

    assert "audit_logs" in note
    assert "decisions/persistent" in note
    assert "v19.0 Persistent Case Review Decisions" in changelog
    assert migration_matches == []
