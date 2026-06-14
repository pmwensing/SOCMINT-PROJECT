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
    set_persistent_decision_review_state,
)
from src.socmint.persistent_decision_supervisor_queue_v19_3 import (
    assign_persistent_decision_reviewer,
)
from src.socmint.reviewer_queue_handoff_summary_routes_v19_6 import (
    register_reviewer_queue_handoff_summary_routes_v19_6,
)
from src.socmint.reviewer_queue_handoff_summary_v19_6 import (
    REVIEWER_QUEUE_HANDOFF_SUMMARY_SCHEMA,
    build_reviewer_queue_handoff_summary,
)


def _configure(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'app.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    database.configure_database(url)


def _app(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    app = create_app()
    register_case_intelligence_review_routes_v18(app)
    register_reviewer_queue_handoff_summary_routes_v19_6(app)
    return app


def _assigned(case_id: str, reviewer: str, decision: str = "approve_review") -> int:
    source = record_case_review_decision(
        case_id,
        {"decision": decision, "note": f"source-{case_id}"},
        operator="analyst",
    )
    persisted = persist_case_review_decision(case_id, source, actor="analyst")
    assign_persistent_decision_reviewer(
        case_id,
        persisted["decision_record_id"],
        reviewer,
        actor="supervisor",
        note=f"assignment-{case_id}",
    )
    return persisted["decision_record_id"]


def test_v19_6_summarizes_completion_follow_up_and_throughput(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    first = _assigned("case-one", "reviewer-a")
    second = _assigned("case-two", "reviewer-a")
    _assigned("case-three", "reviewer-b")
    set_persistent_decision_review_state(
        "case-one", first, "accepted", actor="reviewer-a", note="complete"
    )
    set_persistent_decision_review_state(
        "case-two", second, "needs_follow_up", actor="reviewer-a", note="verify"
    )

    result = build_reviewer_queue_handoff_summary()

    assert result["schema"] == REVIEWER_QUEUE_HANDOFF_SUMMARY_SCHEMA
    assert result["completed_count"] == 1
    assert result["follow_up_count"] == 1
    assert result["outstanding_count"] == 1
    assert result["handoff_ready"] is False
    reviewer = {row["reviewer"]: row for row in result["reviewer_summaries"]}
    assert reviewer["reviewer-a"]["assigned"] == 2
    assert reviewer["reviewer-a"]["completed"] == 1
    assert reviewer["reviewer-a"]["follow_up"] == 1
    assert reviewer["reviewer-a"]["completion_rate"] == 50.0
    assert reviewer["reviewer-b"]["outstanding"] == 1


def test_v19_6_marks_case_and_global_handoff_ready(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    first = _assigned("case-one", "reviewer-a")
    second = _assigned("case-one", "reviewer-b")
    set_persistent_decision_review_state(
        "case-one", first, "reviewed", actor="reviewer-a"
    )
    set_persistent_decision_review_state(
        "case-one", second, "accepted", actor="reviewer-b"
    )

    result = build_reviewer_queue_handoff_summary()

    assert result["handoff_ready"] is True
    assert result["status"] == "ready_for_handoff"
    assert result["next_action"] == "prepare_supervisor_handoff"
    assert result["case_summaries"][0]["handoff_ready"] is True
    assert result["case_summaries"][0]["reviewers"] == [
        "reviewer-a",
        "reviewer-b",
    ]


def test_v19_6_filters_reviewer_and_case(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    _assigned("case-one", "reviewer-a")
    _assigned("case-two", "reviewer-b")

    by_reviewer = build_reviewer_queue_handoff_summary(reviewer="reviewer-a")
    by_case = build_reviewer_queue_handoff_summary(case_id="case-two")

    assert by_reviewer["entry_count"] == 1
    assert by_reviewer["reviewer_summaries"][0]["reviewer"] == "reviewer-a"
    assert by_case["entry_count"] == 1
    assert by_case["case_summaries"][0]["case_id"] == "case-two"


def test_v19_6_routes_require_login_and_render(tmp_path, monkeypatch):
    client = _app(tmp_path, monkeypatch).test_client()
    assert client.get(
        "/api/v1/case-intelligence-review/reviewer-handoff-summary"
    ).status_code == 401
    assert client.get(
        "/case-intelligence-review/reviewer-handoff-summary"
    ).status_code == 302

    _assigned("case-alpha", "reviewer-a")
    with client.session_transaction() as sess:
        sess["user"] = "supervisor"

    api = client.get(
        "/api/v1/case-intelligence-review/reviewer-handoff-summary"
        "?reviewer=reviewer-a"
    )
    ui = client.get("/case-intelligence-review/reviewer-handoff-summary")

    assert api.status_code == 200
    assert api.get_json()["entry_count"] == 1
    assert ui.status_code == 200
    assert b"Reviewer Queue Completion / Handoff Summary" in ui.data
    assert b"Reviewer Throughput" in ui.data
    assert b"Case Handoff Readiness" in ui.data
    assert b"Open case workspace" in ui.data


def test_v19_6_release_note_and_no_migration():
    note = Path(
        "release/V19_6_REVIEWER_QUEUE_COMPLETION_HANDOFF_SUMMARY.md"
    ).read_text(encoding="utf-8")
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v19_6*")
    ]
    assert "reviewer throughput" in note
    assert "handoff readiness" in note
    assert "without mutating" in note
    assert migrations == []
