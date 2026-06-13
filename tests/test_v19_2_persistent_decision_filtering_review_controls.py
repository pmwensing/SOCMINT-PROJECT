from __future__ import annotations

import json
from datetime import datetime
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
    REVIEW_ACTION,
    list_persistent_case_review_decisions,
    persist_case_review_decision,
    set_persistent_decision_review_state,
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


def _seed(case_id, decision, actor, note, recorded_at):
    source = record_case_review_decision(
        case_id,
        {"decision": decision, "note": note},
        operator=actor,
        recorded_at=recorded_at,
    )
    return persist_case_review_decision(case_id, source, actor=actor)


def _set_persisted_at(record_id: int, value: datetime):
    session = database.Session()
    try:
        row = session.query(database.AuditLog).filter_by(id=record_id).one()
        row.created_at = value
        session.commit()
    finally:
        session.close()


def test_v19_2_filters_actor_decision_and_dates(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    first = _seed(
        "case-alpha",
        "approve_review",
        "analyst-a",
        "approved",
        "2026-06-01T10:00:00+00:00",
    )
    second = _seed(
        "case-alpha",
        "needs_follow_up",
        "analyst-b",
        "follow up",
        "2026-06-10T10:00:00+00:00",
    )
    _set_persisted_at(first["decision_record_id"], datetime(2026, 6, 2, 12, 0, 0))
    _set_persisted_at(second["decision_record_id"], datetime(2026, 6, 11, 12, 0, 0))

    by_actor = list_persistent_case_review_decisions(
        "case-alpha", actor="analyst-b"
    )
    by_decision = list_persistent_case_review_decisions(
        "case-alpha", decision="approve_review"
    )
    by_date = list_persistent_case_review_decisions(
        "case-alpha", date_from="2026-06-10", date_to="2026-06-12"
    )

    assert by_actor["total_entries"] == 1
    assert by_actor["entries"][0]["decision"] == "needs_follow_up"
    assert by_decision["total_entries"] == 1
    assert by_decision["entries"][0]["actor"] == "analyst-a"
    assert by_date["total_entries"] == 1
    assert by_date["entries"][0]["decision_record_id"] == second["decision_record_id"]


def test_v19_2_paginates_durable_history(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    for index in range(5):
        _seed(
            "case-alpha",
            "approve_review",
            f"analyst-{index}",
            f"note-{index}",
            f"2026-06-{index + 1:02d}T10:00:00+00:00",
        )

    first_page = list_persistent_case_review_decisions(
        "case-alpha", page=1, page_size=2
    )
    third_page = list_persistent_case_review_decisions(
        "case-alpha", page=3, page_size=2
    )

    assert first_page["entry_count"] == 2
    assert first_page["total_entries"] == 5
    assert first_page["pagination"] == {
        "page": 1,
        "page_size": 2,
        "page_count": 3,
        "has_previous": False,
        "has_next": True,
    }
    assert third_page["entry_count"] == 1
    assert third_page["pagination"]["has_previous"] is True
    assert third_page["pagination"]["has_next"] is False


def test_v19_2_review_state_is_separate_immutable_annotation(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    persisted = _seed(
        "case-alpha",
        "hold_delivery",
        "analyst",
        "original note",
        "2026-06-13T02:00:00+00:00",
    )
    record_id = persisted["decision_record_id"]

    session = database.Session()
    try:
        original = session.query(database.AuditLog).filter_by(id=record_id).one()
        original_details = original.details
    finally:
        session.close()

    result = set_persistent_decision_review_state(
        "case-alpha",
        record_id,
        "reviewed",
        actor="reviewer",
        note="confirmed against evidence",
    )

    assert result["status"] == "recorded"
    assert result["original_decision_mutated"] is False

    session = database.Session()
    try:
        source = session.query(database.AuditLog).filter_by(id=record_id).one()
        annotations = session.query(database.AuditLog).filter_by(
            action=REVIEW_ACTION, target_value="case-alpha"
        ).all()
        assert source.action == AUDIT_ACTION
        assert source.details == original_details
        assert len(annotations) == 1
        assert json.loads(annotations[0].details)["decision_record_id"] == record_id
    finally:
        session.close()

    history = list_persistent_case_review_decisions(
        "case-alpha", review_state="reviewed"
    )
    assert history["total_entries"] == 1
    assert history["entries"][0]["review_state"] == "reviewed"
    assert history["entries"][0]["reviewed_by"] == "reviewer"
    assert history["entries"][0]["review_note"] == "confirmed against evidence"
    assert history["original_records_mutated"] is False


def test_v19_2_rejects_invalid_review_state_and_wrong_case(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    persisted = _seed(
        "case-alpha",
        "approve_review",
        "analyst",
        "note",
        "2026-06-13T02:00:00+00:00",
    )

    invalid = set_persistent_decision_review_state(
        "case-alpha",
        persisted["decision_record_id"],
        "deleted",
        actor="reviewer",
    )
    wrong_case = set_persistent_decision_review_state(
        "case-other",
        persisted["decision_record_id"],
        "reviewed",
        actor="reviewer",
    )

    assert invalid["status"] == "blocked"
    assert invalid["blockers"][0]["key"] == "unsupported_review_state"
    assert wrong_case["status"] == "blocked"
    assert wrong_case["blockers"][0]["key"] == "decision_record_not_found"


def test_v19_2_routes_filter_paginate_and_record_review_state(tmp_path, monkeypatch):
    client = _app(tmp_path, monkeypatch).test_client()
    with client.session_transaction() as sess:
        sess["user"] = "reviewer"
        sess["_csrf_token"] = "test-csrf"

    first = client.post(
        "/api/v1/case-intelligence-review/case-alpha/decisions",
        json={"decision": "approve_review", "note": "first"},
        headers={"X-CSRF-Token": "test-csrf"},
    ).get_json()["persistent_decision"]
    client.post(
        "/api/v1/case-intelligence-review/case-alpha/decisions",
        json={"decision": "needs_follow_up", "note": "second"},
        headers={"X-CSRF-Token": "test-csrf"},
    )

    filtered = client.get(
        "/api/v1/case-intelligence-review/case-alpha/decisions/persistent"
        "?decision=approve_review&page=1&page_size=1"
    )
    annotated = client.post(
        f"/api/v1/case-intelligence-review/case-alpha/decisions/"
        f"{first['decision_record_id']}/review-state",
        json={"review_state": "accepted", "note": "supervisor accepted"},
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert filtered.status_code == 200
    assert filtered.get_json()["total_entries"] == 1
    assert filtered.get_json()["pagination"]["page_size"] == 1
    assert annotated.status_code == 200
    assert annotated.get_json()["review_state"] == "accepted"
    assert annotated.get_json()["persistent_decision_history"]["entries"][0][
        "review_state"
    ] == "accepted"


def test_v19_2_ui_and_client_controls_are_present(tmp_path, monkeypatch):
    client = _app(tmp_path, monkeypatch).test_client()
    with client.session_transaction() as sess:
        sess["user"] = "reviewer"

    response = client.get("/case-intelligence-review/case-alpha")
    script = Path("src/socmint/static/case_intelligence_review_v18.js").read_text(
        encoding="utf-8"
    )

    assert response.status_code == 200
    assert b"persistent-filter-actor" in response.data
    assert b"persistent-filter-decision" in response.data
    assert b"persistent-filter-date-from" in response.data
    assert b"persistent-filter-review-state" in response.data
    assert b"persistent-page-previous" in response.data
    assert b"save-persistent-review-state" in response.data or b"Review control" in response.data
    assert "persistentQuery" in script
    assert "saveReviewState" in script
    assert "review-state" in script


def test_v19_2_release_note_and_no_migration():
    note = Path(
        "release/V19_2_PERSISTENT_DECISION_FILTERING_REVIEW_CONTROLS.md"
    ).read_text(encoding="utf-8")
    migration_matches = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v19_2*")
    ]

    assert "actor, decision, and date filtering" in note
    assert "pagination" in note
    assert "immutable" in note
    assert migration_matches == []
