from pathlib import Path

from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import register_dossier_assembly_routes_v21_0


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def test_v25_0_routes_apply_session_case_scope_and_render(tmp_path, monkeypatch):
    from src.socmint import cross_case_intelligence_routes_v25_0 as routes

    calls = []

    def build(**kwargs):
        calls.append(kwargs)
        return {
            "schema": "socmint.cross_case_intelligence_workspace.v25_0",
            "version": "v25.0.0",
            "status": "ready",
            "minimum_case_count": kwargs["minimum_case_count"],
            "access_scope": {
                "mode": "restricted",
                "allowed_case_ids": sorted(kwargs["allowed_case_ids"]),
                "visible_case_ids": ["case-alpha", "case-bravo"],
            },
            "counts": {
                "visible_cases": 2,
                "source_records": 4,
                "entity_correlations": 1,
                "identifier_correlations": 1,
                "infrastructure_correlations": 1,
                "evidence_correlations": 1,
                "timeline_correlations": 1,
                "repeated_patterns": 1,
            },
            "correlations": {
                "entities": [{
                    "correlation_id": "cross-case-entity-1",
                    "category": "entity",
                    "match_value": "entity-42",
                    "display_values": ["entity-42"],
                    "case_ids": ["case-alpha", "case-bravo"],
                    "case_count": 2,
                    "occurrence_count": 2,
                    "occurrences": [
                        {"case_id": "case-alpha", "record_id": 1, "source_action": "case_entity_observed", "field_path": "entity_id", "actor": "analyst-a", "occurred_at": "2026-06-16T02:00:00+00:00"},
                        {"case_id": "case-bravo", "record_id": 2, "source_action": "case_entity_observed", "field_path": "entity_id", "actor": "analyst-b", "occurred_at": "2026-06-16T03:00:00+00:00"},
                    ],
                    "human_review_required": True,
                    "confirmed_match": False,
                }],
                "identifiers": [],
                "infrastructure": [],
                "evidence": [],
                "timelines": [],
            },
            "repeated_patterns": [{
                "pattern_type": "repeated_action",
                "pattern": "case_entity_observed",
                "case_ids": ["case-alpha", "case-bravo"],
                "case_count": 2,
                "occurrence_count": 2,
                "human_review_required": True,
            }],
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

    monkeypatch.setattr(routes, "build_cross_case_intelligence_workspace", build)

    client = _app(tmp_path, monkeypatch).test_client()
    assert client.get("/api/v1/cross-case-intelligence").status_code == 401
    assert client.get("/cross-case-intelligence").status_code in {302, 303}

    with client.session_transaction() as sess:
        sess["user"] = "analyst"
        sess["allowed_case_ids"] = ["case-alpha", "case-bravo"]

    ui = client.get("/cross-case-intelligence?minimum_case_count=2")
    api = client.get("/api/v1/cross-case-intelligence?minimum_case_count=2")

    assert ui.status_code == 200
    assert b"Cross-Case Intelligence Workspace" in ui.data
    assert b"Correlation Summary" in ui.data
    assert b"Access Scope" in ui.data
    assert b"entity-42" in ui.data
    assert b"case-alpha" in ui.data
    assert b"case-bravo" in ui.data
    assert b"candidates requiring human review" in ui.data
    assert api.status_code == 200
    assert api.get_json()["counts"]["visible_cases"] == 2
    assert all(call["allowed_case_ids"] == {"case-alpha", "case-bravo"} for call in calls)
    assert all(call["minimum_case_count"] == 2 for call in calls)


def test_v25_0_invalid_minimum_falls_back_and_empty_scope_is_restricted(tmp_path, monkeypatch):
    from src.socmint import cross_case_intelligence_routes_v25_0 as routes

    captured = {}

    def build(**kwargs):
        captured.update(kwargs)
        return {
            "schema": "socmint.cross_case_intelligence_workspace.v25_0",
            "version": "v25.0.0",
            "status": "ready",
            "minimum_case_count": kwargs["minimum_case_count"],
            "access_scope": {"mode": "restricted", "allowed_case_ids": [], "visible_case_ids": []},
            "counts": {"visible_cases": 0, "source_records": 0, "entity_correlations": 0, "identifier_correlations": 0, "infrastructure_correlations": 0, "evidence_correlations": 0, "timeline_correlations": 0, "repeated_patterns": 0},
            "correlations": {"entities": [], "identifiers": [], "infrastructure": [], "evidence": [], "timelines": []},
            "repeated_patterns": [],
            "case_provenance": {},
            "links": {"portfolio_operations": "/portfolio-operations", "portfolio_history": "/portfolio-operations/history"},
            "human_review_required": True,
            "correlations_are_candidates": True,
            "source_records_mutated": False,
            "correlation_record_created": False,
            "next_action": "review_cross_case_candidates",
        }

    monkeypatch.setattr(routes, "build_cross_case_intelligence_workspace", build)
    client = _app(tmp_path, monkeypatch).test_client()
    with client.session_transaction() as sess:
        sess["user"] = "analyst"
        sess["allowed_case_ids"] = "invalid"

    response = client.get("/api/v1/cross-case-intelligence?minimum_case_count=bad")
    assert response.status_code == 200
    assert captured["allowed_case_ids"] == set()
    assert captured["minimum_case_count"] == 2


def test_v25_0_release_note_and_no_migration():
    note = Path("release/V25_0_CROSS_CASE_INTELLIGENCE_WORKSPACE.md").read_text(encoding="utf-8")
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v25_0*")
    ]
    assert "entities, identifiers, infrastructure, evidence, timelines, and repeated patterns" in note
    assert "case-level provenance" in note
    assert "access controls" in note
    assert "candidate correlations" in note
    assert "human review" in note
    assert "read-only" in note
    assert migrations == []
