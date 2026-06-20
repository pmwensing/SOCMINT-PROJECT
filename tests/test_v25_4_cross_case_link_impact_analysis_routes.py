from pathlib import Path

from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import (
    register_dossier_assembly_routes_v21_0,
)


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def test_v25_4_impact_routes_apply_scope_and_render(tmp_path, monkeypatch):
    from src.socmint import cross_case_intelligence_routes_v25_0 as routes

    captured = []
    payload = {
        "schema": "socmint.cross_case_link_impact_analysis.v25_4",
        "version": "v25.4.0",
        "status": "ready",
        "access_scope": {
            "mode": "restricted",
            "allowed_case_ids": ["case-alpha", "case-bravo"],
        },
        "impact": {
            "confirmed_link_id": "confirmed-link-1",
            "confirmed_link_sha256": "f" * 64,
            "accepted_review_decision_id": "review-1",
            "accepted_review_decision_sha256": "d" * 64,
            "affected_case_ids": ["case-alpha", "case-bravo"],
            "affected_entities": [
                {
                    "node_id": "entity-1",
                    "node_type": "entity",
                    "label": "entity-42",
                    "confirmed_link_ids": ["confirmed-link-1"],
                    "source_occurrences": [{"case_id": "case-alpha"}],
                }
            ],
            "evidence_packages": [
                {
                    "case_id": "case-alpha",
                    "record_id": 10,
                    "action": "dossier_final_export_package",
                    "actor": "reviewer",
                    "occurred_at": "2026-06-16T05:00:00+00:00",
                }
            ],
            "review_queues": [
                {
                    "case_id": "case-alpha",
                    "review_state": "unreviewed",
                    "assigned_reviewer": "alice",
                    "assignment_age_hours": 12.0,
                    "reviewer_queue": "/case-intelligence-review/my-assignments",
                    "supervisor_queue": "/case-intelligence-review/supervisor-queue?assigned_reviewer=alice",
                }
            ],
            "closure_states": [
                {
                    "case_id": "case-alpha",
                    "current_closure_state": "closed",
                    "current_archive_state": "generated",
                    "retention_disposition": "retain_until_expiration",
                    "reopen_status": "none",
                    "unresolved_actions": [],
                    "history_event_count": 5,
                }
            ],
            "archive_records": [
                {
                    "case_id": "case-alpha",
                    "timeline_id": 20,
                    "actor": "archivist",
                    "occurred_at": "2026-06-16T06:00:00+00:00",
                }
            ],
            "graph_node_ids": ["case-a", "entity-1"],
            "graph_edge_ids": ["edge-1"],
        },
        "impact_sha256": "i" * 64,
        "counts": {
            "affected_cases": 2,
            "affected_entities": 1,
            "entities_by_type": {"entity": 1},
            "evidence_packages": 1,
            "review_queue_entries": 1,
            "closure_states": 1,
            "archive_records": 1,
            "graph_nodes": 2,
            "graph_edges": 1,
        },
        "confirmed_link_binding": {
            "confirmed_link_id": "confirmed-link-1",
            "confirmed_link_sha256": "f" * 64,
            "registry_record_id": 31,
            "accepted_review_decision_id": "review-1",
            "accepted_review_decision_sha256": "d" * 64,
            "source_occurrences_sha256": "o" * 64,
        },
        "graph_binding": {
            "graph_sha256": "g" * 64,
            "graph_node_ids": ["case-a", "entity-1"],
            "graph_edge_ids": ["edge-1"],
        },
        "confirmed_link_mutated": False,
        "graph_mutated": False,
        "source_records_mutated": False,
        "impact_record_created": False,
        "next_action": "review_cross_case_link_impact",
    }

    def build(link_id, **kwargs):
        captured.append((link_id, kwargs))
        return payload

    monkeypatch.setattr(routes, "build_cross_case_link_impact_analysis", build)
    client = _app(tmp_path, monkeypatch).test_client()
    assert (
        client.get(
            "/api/v1/cross-case-intelligence/confirmed-links/confirmed-link-1/impact"
        ).status_code
        == 401
    )
    assert client.get(
        "/cross-case-intelligence/confirmed-links/confirmed-link-1/impact"
    ).status_code in {302, 303}

    with client.session_transaction() as sess:
        sess["user"] = "analyst"
        sess["allowed_case_ids"] = ["case-alpha", "case-bravo"]

    ui = client.get("/cross-case-intelligence/confirmed-links/confirmed-link-1/impact")
    api = client.get(
        "/api/v1/cross-case-intelligence/confirmed-links/confirmed-link-1/impact"
    )
    assert ui.status_code == 200
    assert b"Cross-Case Link Impact Analysis" in ui.data
    assert b"Affected Cases" in ui.data
    assert b"Affected Entities and Graph Nodes" in ui.data
    assert b"Evidence Packages" in ui.data
    assert b"Review Queue Impact" in ui.data
    assert b"Archive Records" in ui.data
    assert b"confirmed-link registry and relationship graph remain unchanged" in ui.data
    assert api.status_code == 200
    assert api.get_json()["counts"]["affected_cases"] == 2
    assert all(
        item[1]["allowed_case_ids"] == {"case-alpha", "case-bravo"} for item in captured
    )


def test_v25_4_missing_link_returns_404(tmp_path, monkeypatch):
    from src.socmint import cross_case_intelligence_routes_v25_0 as routes

    monkeypatch.setattr(
        routes,
        "build_cross_case_link_impact_analysis",
        lambda *args, **kwargs: {
            "schema": "socmint.cross_case_link_impact_analysis.v25_4",
            "version": "v25.4.0",
            "status": "blocked",
            "blockers": [{"key": "visible_confirmed_link_required"}],
            "confirmed_link_mutated": False,
            "graph_mutated": False,
        },
    )
    client = _app(tmp_path, monkeypatch).test_client()
    with client.session_transaction() as sess:
        sess["user"] = "analyst"
    assert (
        client.get(
            "/api/v1/cross-case-intelligence/confirmed-links/missing/impact"
        ).status_code
        == 404
    )
    assert (
        client.get(
            "/cross-case-intelligence/confirmed-links/missing/impact"
        ).status_code
        == 404
    )


def test_v25_4_release_note_and_no_migration():
    note = Path("release/V25_4_CROSS_CASE_LINK_IMPACT_ANALYSIS.md").read_text(
        encoding="utf-8"
    )
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v25_4*")
    ]
    assert (
        "affected cases, entities, evidence packages, review queues, closure states, and archive records"
        in note
    )
    assert "confirmed-link binding" in note
    assert "graph binding" in note
    assert "impact SHA-256" in note
    assert "confirmed-link and graph records unchanged" in note
    assert "read-only" in note
    assert migrations == []
