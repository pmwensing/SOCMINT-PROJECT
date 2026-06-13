from __future__ import annotations

from pathlib import Path

from src.socmint.case_intelligence_review_routes_v18 import register_case_intelligence_review_routes_v18
from src.socmint.case_intelligence_review_workspace_v18 import (
    CASE_INTELLIGENCE_REVIEW_WORKSPACE_SCHEMA,
    append_case_review_history,
    build_case_intelligence_review_workspace,
    build_v18_product_review_checkpoint,
    record_case_review_decision,
)
from src.socmint.dashboard import create_app


def _app():
    app = create_app()
    register_case_intelligence_review_routes_v18(app)
    return app


def _payload():
    return {
        "title": "Case Alpha",
        "evidence": [{"evidence_id": "ev-1", "source": "capture"}],
        "claims": [
            {"id": "cl-1", "text": "Supported claim", "status": "supported", "evidence_ids": ["ev-1"]},
            {"id": "cl-2", "text": "Open claim", "status": "review", "evidence_ids": ["missing"]},
        ],
        "identities": [{"id": "id-1", "name": "Candidate", "confidence": 0.55, "status": "candidate"}],
        "entities": [{"id": "en-1", "name": "Resolved org", "confidence": 0.94, "status": "resolved"}],
        "timeline": [
            {"id": "t-2", "occurred_at": "2026-02-02T00:00:00Z", "event": "Second"},
            {"id": "t-1", "occurred_at": "2026-01-01T00:00:00Z", "event": "First"},
        ],
        "contradictions": [{"id": "cx-1", "summary": "Date conflict", "status": "open"}],
    }


def test_v18_workspace_combines_all_review_panels():
    result = build_case_intelligence_review_workspace("case-alpha", _payload(), operator="analyst")
    assert result["schema"] == CASE_INTELLIGENCE_REVIEW_WORKSPACE_SCHEMA
    assert result["summary"]["evidence_count"] == 1
    assert result["summary"]["claim_count"] == 2
    assert result["evidence_claim_review"]["broken_link_count"] == 1
    assert result["identity_entity_review"]["review_required_count"] == 1
    assert result["timeline_contradiction_review"]["events"][0]["id"] == "t-1"
    assert result["timeline_contradiction_review"]["open_contradiction_count"] == 1
    assert result["status"] == "review_required"


def test_v18_summary_cards_mark_clean_case_ready():
    payload = {"evidence": [], "claims": [], "identities": [], "entities": [], "timeline": [], "contradictions": []}
    result = build_case_intelligence_review_workspace("case-clean", payload)
    assert result["status"] == "ready_for_analyst_decision"
    assert result["next_action"] == "record_analyst_decision"


def test_v18_decision_actions_and_session_history():
    decision = record_case_review_decision(
        "case-alpha",
        {"decision": "approve_review", "note": "review complete"},
        operator="analyst",
        recorded_at="2026-06-12T23:30:00+00:00",
    )
    history = append_case_review_history([], decision)
    workspace = build_case_intelligence_review_workspace("case-alpha", {}, history=history, operator="analyst")
    assert decision["status"] == "recorded"
    assert workspace["review_history"]["entry_count"] == 1
    assert workspace["review_history"]["entries"][0]["decision"] == "approve_review"


def test_v18_unsupported_decision_is_blocked():
    result = record_case_review_decision("case-alpha", {"decision": "delete_case"}, operator="analyst")
    assert result["status"] == "blocked"
    assert result["blockers"][0]["key"] == "unsupported_decision"


def test_v18_routes_require_login(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    client = _app().test_client()
    assert client.get("/api/v1/case-intelligence-review/case-alpha").status_code == 401
    assert client.get("/case-intelligence-review/case-alpha").status_code == 302


def test_v18_api_and_decision_history_routes(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    client = _app().test_client()
    with client.session_transaction() as sess:
        sess["user"] = "analyst"
        sess["_csrf_token"] = "test-csrf"
    workspace = client.post(
        "/api/v1/case-intelligence-review/case-alpha",
        json=_payload(),
        headers={"X-CSRF-Token": "test-csrf"},
    )
    decision = client.post(
        "/api/v1/case-intelligence-review/case-alpha/decisions",
        json={"decision": "needs_follow_up", "note": "verify date"},
        headers={"X-CSRF-Token": "test-csrf"},
    )
    history = client.get("/api/v1/case-intelligence-review/case-alpha/history")
    assert workspace.status_code == 200
    assert decision.status_code == 200
    assert history.get_json()["entry_count"] == 1


def test_v18_ui_and_static_script_render(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    client = _app().test_client()
    with client.session_transaction() as sess:
        sess["user"] = "analyst"
    response = client.get("/case-intelligence-review/case-alpha")
    assert response.status_code == 200
    assert b"Case Intelligence Review Workspace" in response.data
    assert b"Evidence and Claim Review" in response.data
    assert b"Identity and Entity Resolution" in response.data
    assert b"Timeline and Contradiction Review" in response.data
    assert b"case_intelligence_review_v18.js" in response.data


def test_v18_product_review_checkpoint_is_ready():
    app = _app()
    result = build_v18_product_review_checkpoint(routes=list(app.url_map.iter_rules()))
    assert result["ready"] is True
    assert result["status"] == "ready_for_browser_validation"
    assert result["migration_artifacts"] == []


def test_v18_release_notes_and_changelog_are_present():
    for index in range(8):
        assert list(Path("release").glob(f"V18_{index}_*.md"))
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")
    for index in range(8):
        assert f"v18.{index}" in changelog
