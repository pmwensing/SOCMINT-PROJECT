from __future__ import annotations

from datetime import UTC, datetime
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
    set_persistent_decision_review_state,
)
from src.socmint.persistent_decision_supervisor_queue_v19_3 import (
    PERSISTENT_DECISION_SUPERVISOR_QUEUE_SCHEMA,
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


def _seed(case_id, decision, actor, recorded_at):
    source = record_case_review_decision(
        case_id,
        {"decision": decision, "note": f"note-{case_id}"},
        operator=actor,
        recorded_at=recorded_at,
    )
    return persist_case_review_decision(case_id, source, actor=actor)


def _set_created_at(record_id, created_at):
    session = database.Session()
    try:
        row = session.query(database.AuditLog).filter_by(id=record_id).one()
        row.created_at = created_at
        session.commit()
    finally:
        session.close()


def test_v19_3_cross_case_counts_oldest_age_and_reviewers(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    first = _seed(
        "case-one", "approve_review", "analyst-a", "2026-06-10T00:00:00+00:00"
    )
    second = _seed(
        "case-two", "needs_follow_up", "analyst-b", "2026-06-11T00:00:00+00:00"
    )
    third = _seed("case-two", "hold_delivery", "analyst-c", "2026-06-12T00:00:00+00:00")
    _set_created_at(first["decision_record_id"], datetime(2026, 6, 10, tzinfo=UTC))
    _set_created_at(second["decision_record_id"], datetime(2026, 6, 11, tzinfo=UTC))
    _set_created_at(third["decision_record_id"], datetime(2026, 6, 12, tzinfo=UTC))
    set_persistent_decision_review_state(
        "case-two",
        second["decision_record_id"],
        "needs_follow_up",
        actor="reviewer-a",
        note="verify",
    )
    set_persistent_decision_review_state(
        "case-two", third["decision_record_id"], "accepted", actor="reviewer-b"
    )

    result = build_persistent_decision_supervisor_queue(
        now=datetime(2026, 6, 13, tzinfo=UTC)
    )

    assert result["schema"] == PERSISTENT_DECISION_SUPERVISOR_QUEUE_SCHEMA
    assert result["counts"] == {
        "accepted": 1,
        "needs_follow_up": 1,
        "reviewed": 0,
        "unreviewed": 1,
    }
    assert result["total_decisions"] == 3
    assert result["total_outstanding"] == 2
    assert result["oldest_outstanding_age_hours"] == 72.0
    assert result["assigned_reviewers"] == ["reviewer-a", "reviewer-b"]
    assert result["entries"][0]["case_id"] == "case-one"


def test_v19_3_case_summaries_filters_and_links(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    first = _seed("case-one", "approve_review", "analyst", "2026-06-10T00:00:00+00:00")
    second = _seed("case-two", "hold_delivery", "analyst", "2026-06-11T00:00:00+00:00")
    set_persistent_decision_review_state(
        "case-one", first["decision_record_id"], "reviewed", actor="reviewer-a"
    )
    set_persistent_decision_review_state(
        "case-two", second["decision_record_id"], "needs_follow_up", actor="reviewer-b"
    )

    result = build_persistent_decision_supervisor_queue()
    summaries = {item["case_id"]: item for item in result["case_summaries"]}
    assert summaries["case-one"]["reviewed"] == 1
    assert summaries["case-two"]["outstanding"] == 1
    assert (
        summaries["case-one"]["case_workspace_href"]
        == "/case-intelligence-review/case-one"
    )
    assert (
        build_persistent_decision_supervisor_queue(case_id="case-one")["entry_count"]
        == 1
    )
    assert (
        build_persistent_decision_supervisor_queue(review_state="needs_follow_up")[
            "entries"
        ][0]["case_id"]
        == "case-two"
    )
    assert (
        build_persistent_decision_supervisor_queue(assigned_reviewer="reviewer-a")[
            "entries"
        ][0]["case_id"]
        == "case-one"
    )
