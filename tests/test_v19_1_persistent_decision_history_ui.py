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
    persist_case_review_decision,
)


def _app(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'app.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    database.configure_database(database_url)
    app = create_app()
    register_case_intelligence_review_routes_v18(app)
    return app


def _seed_decision(case_id="case-alpha"):
    decision = record_case_review_decision(
        case_id,
        {"decision": "approve_review", "note": "durable review"},
        operator="analyst",
        recorded_at="2026-06-13T02:00:00+00:00",
    )
    return persist_case_review_decision(
        case_id,
        decision,
        actor="analyst",
        ip_address="127.0.0.1",
    )


def test_v19_1_workspace_api_includes_persistent_history(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    _seed_decision()
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user"] = "analyst"

    response = client.get("/api/v1/case-intelligence-review/case-alpha")

    assert response.status_code == 200
    payload = response.get_json()
    history = payload["persistent_decision_history"]
    assert history["entry_count"] == 1
    assert history["entries"][0]["actor"] == "analyst"
    assert history["entries"][0]["decision"] == "approve_review"
    assert history["entries"][0]["note"] == "durable review"
    assert history["entries"][0]["source_recorded_at"] == "2026-06-13T02:00:00+00:00"
    assert history["entries"][0]["persisted_at"]


def test_v19_1_workspace_renders_durable_and_session_sections_separately(
    tmp_path, monkeypatch
):
    app = _app(tmp_path, monkeypatch)
    _seed_decision()
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user"] = "analyst"

    response = client.get("/case-intelligence-review/case-alpha")

    assert response.status_code == 200
    assert b"Persistent Decision History" in response.data
    assert b"Case Review Session History" in response.data
    assert b"Durable case decisions" in response.data
    assert b"Temporary decisions visible only" in response.data
    assert b"durable review" in response.data
    assert b"2026-06-13T02:00:00+00:00" in response.data


def test_v19_1_decision_response_returns_both_histories(tmp_path, monkeypatch):
    client = _app(tmp_path, monkeypatch).test_client()
    with client.session_transaction() as sess:
        sess["user"] = "analyst"
        sess["_csrf_token"] = "test-csrf"

    response = client.post(
        "/api/v1/case-intelligence-review/case-alpha/decisions",
        json={
            "decision": "needs_follow_up",
            "note": "verify account ownership",
            "recorded_at": "2026-06-13T02:10:00+00:00",
        },
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["review_history"]["entry_count"] == 1
    assert payload["persistent_decision_history"]["entry_count"] == 1
    assert payload["persistent_decision_history"]["entries"][0]["decision"] == "needs_follow_up"


def test_v19_1_persistent_ui_survives_session_history_clear(tmp_path, monkeypatch):
    client = _app(tmp_path, monkeypatch).test_client()
    with client.session_transaction() as sess:
        sess["user"] = "analyst"
        sess["_csrf_token"] = "test-csrf"

    client.post(
        "/api/v1/case-intelligence-review/case-alpha/decisions",
        json={"decision": "hold_delivery", "note": "open contradiction"},
        headers={"X-CSRF-Token": "test-csrf"},
    )

    with client.session_transaction() as sess:
        user = sess["user"]
        sess.clear()
        sess["user"] = user

    response = client.get("/api/v1/case-intelligence-review/case-alpha")
    payload = response.get_json()

    assert payload["review_history"]["entry_count"] == 0
    assert payload["persistent_decision_history"]["entry_count"] == 1
    assert payload["persistent_decision_history"]["entries"][0]["decision"] == "hold_delivery"


def test_v19_1_client_script_refreshes_persistent_history():
    script = Path("src/socmint/static/case_intelligence_review_v18.js").read_text(
        encoding="utf-8"
    )

    assert "renderPersistentHistory" in script
    assert "refreshPersistentHistory" in script
    assert "decisions/persistent" in script
    assert "persistentQuery" in script
    assert "Decision recorded and persisted" in script


def test_v19_1_release_note_is_present():
    note = Path("release/V19_1_PERSISTENT_DECISION_HISTORY_UI.md").read_text(
        encoding="utf-8"
    )

    assert "Persistent Decision History" in note
    assert "source timestamp" in note
    assert "persistence timestamp" in note
