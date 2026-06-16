from pathlib import Path

from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import register_dossier_assembly_routes_v21_0


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def test_v25_1_review_routes_and_workspace_ui(tmp_path, monkeypatch):
    from src.socmint import cross_case_intelligence_routes_v25_0 as routes

    workspace = {
        "schema": "socmint.cross_case_intelligence_workspace.v25_0",
        "version": "v25.0.0",
        "status": "ready",
        "minimum_case_count": 2,
        "access_scope": {
            "mode": "restricted",
            "allowed_case_ids": ["case-alpha", "case-bravo"],
            "visible_case_ids": ["case-alpha", "case-bravo"],
        },
        "counts": {
            "visible_cases": 2,
            "source_records": 2,
            "entity_correlations": 1,
            "identifier_correlations": 0,
            "infrastructure_correlations": 0,
            "evidence_correlations": 0,
            "timeline_correlations": 0,
            "repeated_patterns": 0,
        },
        "correlations": {
            "entities": [{
                "correlation_id": "cross-case-entity-abc",
                "category": "entity",
                "match_value": "entity-42",
                "display_values": ["entity-42"],
                "case_ids": ["case-alpha", "case-bravo"],
                "case_count": 2,
                "occurrence_count": 2,
                "occurrences": [
                    {
                        "case_id": "case-alpha",
                        "record_id": 1,
                        "source_action": "case_entity_observed",
                        "field_path": "entity_id",
                        "actor": "analyst-a",
                        "occurred_at": "2026-06-16T02:00:00+00:00",
                        "provenance_sha256": "a" * 64,
                    },
                    {
                        "case_id": "case-bravo",
                        "record_id": 2,
                        "source_action": "case_entity_observed",
                        "field_path": "entity_id",
                        "actor": "analyst-b",
                        "occurred_at": "2026-06-16T03:00:00+00:00",
                        "provenance_sha256": "b" * 64,
                    },
                ],
                "human_review_required": True,
                "confirmed_match": False,
            }],
            "identifiers": [],
            "infrastructure": [],
            "evidence": [],
            "timelines": [],
        },
        "repeated_patterns": [],
        "case_provenance": {},
        "links": {
            "portfolio_operations": "/portfolio-operations",
            "portfolio_history": "/portfolio-operations/history",
        },
        "human_review_required": True,
        "correlations_are_candidates": True,
        "source_records_mutated": False,
        "correlation_record_created": False,
        "next_action": "review_cross_case_candidates",
    }
    history = [{
        "correlation_id": "cross-case-entity-abc",
        "decision": "defer",
        "reason": "Await another source.",
        "reviewer": "reviewer-old",
        "action_record_id": 7,
    }]

    monkeypatch.setattr(routes, "build_cross_case_intelligence_workspace", lambda **kwargs: workspace)
    monkeypatch.setattr(routes, "correlation_review_history", lambda correlation_id: history)
    monkeypatch.setattr(
        routes,
        "review_correlation_candidate",
        lambda correlation_id, **kwargs: {
            "schema": "socmint.cross_case_correlation_review.v25_1",
            "version": "v25.1.0",
            "correlation_id": correlation_id,
            "decision": kwargs["decision"],
            "reviewer": kwargs["reviewer"],
            "reason": kwargs["reason"],
            "status": "correlation_review_recorded",
            "action_record_id": 8,
            "source_occurrences_preserved": True,
            "source_records_mutated": False,
        },
    )

    client = _app(tmp_path, monkeypatch).test_client()
    assert client.get("/api/v1/cross-case-intelligence/cross-case-entity-abc/reviews").status_code == 401

    with client.session_transaction() as sess:
        sess["user"] = "reviewer-one"
        sess["allowed_case_ids"] = ["case-alpha", "case-bravo"]
        sess["_csrf_token"] = "test-csrf"

    ui = client.get("/cross-case-intelligence")
    assert ui.status_code == 200
    assert b"Record Decision" in ui.data
    assert b"Accept" in ui.data
    assert b"Reject" in ui.data
    assert b"Defer" in ui.data
    assert b"Split" in ui.data
    assert b"Latest decision" in ui.data
    assert b"reviewer-old" in ui.data
    assert b"every source occurrence remains preserved" in ui.data

    review_history = client.get(
        "/api/v1/cross-case-intelligence/cross-case-entity-abc/reviews"
    )
    assert review_history.status_code == 200
    assert review_history.get_json()["history"][0]["decision"] == "defer"

    response = client.post(
        "/api/v1/cross-case-intelligence/cross-case-entity-abc/review",
        json={
            "category": "entity",
            "decision": "accept",
            "reason": "Occurrences represent the same entity.",
            "confirmed": True,
        },
        headers={"X-CSRF-Token": "test-csrf"},
    )
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["decision"] == "accept"
    assert payload["reviewer"] == "reviewer-one"
    assert payload["action_record_id"] == 8


def test_v25_1_blocked_review_returns_422(tmp_path, monkeypatch):
    from src.socmint import cross_case_intelligence_routes_v25_0 as routes

    monkeypatch.setattr(
        routes,
        "review_correlation_candidate",
        lambda *args, **kwargs: {
            "status": "blocked",
            "blockers": [{"key": "correlation_review_reason_required"}],
        },
    )
    client = _app(tmp_path, monkeypatch).test_client()
    with client.session_transaction() as sess:
        sess["user"] = "reviewer-one"
        sess["_csrf_token"] = "test-csrf"

    response = client.post(
        "/api/v1/cross-case-intelligence/candidate/review",
        json={"category": "entity", "decision": "accept", "confirmed": True},
        headers={"X-CSRF-Token": "test-csrf"},
    )
    assert response.status_code == 422
    assert response.get_json()["blockers"][0]["key"] == "correlation_review_reason_required"


def test_v25_1_release_note_client_and_no_migration():
    note = Path("release/V25_1_CORRELATION_CANDIDATE_REVIEW_DECISION.md").read_text(encoding="utf-8")
    script = Path("src/socmint/static/cross_case_correlation_review_v25_1.js").read_text(encoding="utf-8")
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v25_1*")
    ]
    assert "accept, reject, defer, or split" in note
    assert "every source occurrence" in note
    assert "reviewer identity" in note
    assert "decision reason" in note
    assert "immutable audit history" in note
    assert "candidate snapshot" in note
    assert "access scope" in note
    assert "data-action='record-review'" in script
    assert "split_groups" in script
    assert migrations == []
