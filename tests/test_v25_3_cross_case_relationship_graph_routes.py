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


def test_v25_3_graph_routes_apply_scope_and_render(tmp_path, monkeypatch):
    from src.socmint import cross_case_intelligence_routes_v25_0 as routes

    captured = []
    payload = {
        "schema": "socmint.cross_case_relationship_graph.v25_3",
        "version": "v25.3.0",
        "status": "ready",
        "access_scope": {
            "mode": "restricted",
            "allowed_case_ids": ["case-alpha", "case-bravo"],
        },
        "graph": {
            "confirmed_link_ids": ["confirmed-link-1"],
            "nodes": [
                {
                    "node_id": "case-alpha-node",
                    "node_type": "case",
                    "value": "case-alpha",
                    "label": "case-alpha",
                    "confirmed_link_ids": ["confirmed-link-1"],
                    "review_bindings": [
                        {"decision_id": "review-1", "decision_sha256": "d" * 64}
                    ],
                    "source_occurrences": [],
                    "provenance": [{"confirmed_link_id": "confirmed-link-1"}],
                    "node_sha256": "n" * 64,
                },
                {
                    "node_id": "entity-node",
                    "node_type": "entity",
                    "value": "entity-42",
                    "label": "entity-42",
                    "confirmed_link_ids": ["confirmed-link-1"],
                    "review_bindings": [
                        {"decision_id": "review-1", "decision_sha256": "d" * 64}
                    ],
                    "source_occurrences": [{"case_id": "case-alpha", "record_id": 1}],
                    "provenance": [{"confirmed_link_id": "confirmed-link-1"}],
                    "node_sha256": "e" * 64,
                },
            ],
            "edges": [
                {
                    "edge_id": "edge-1",
                    "edge_type": "case_confirmed_link",
                    "source": "case-alpha-node",
                    "target": "entity-node",
                    "confirmed_link_id": "confirmed-link-1",
                    "confirmed_link_sha256": "f" * 64,
                    "accepted_review_decision_id": "review-1",
                    "accepted_review_decision_sha256": "d" * 64,
                    "source_occurrences": [{"case_id": "case-alpha", "record_id": 1}],
                    "source_occurrences_sha256": "o" * 64,
                    "access_scope": {"mode": "restricted"},
                    "provenance": {"registry_record_id": 9},
                    "edge_sha256": "x" * 64,
                }
            ],
        },
        "graph_sha256": "g" * 64,
        "counts": {
            "confirmed_links": 1,
            "nodes": 2,
            "edges": 1,
            "nodes_by_type": {"case": 1, "entity": 1},
            "edges_by_type": {"case_confirmed_link": 1},
        },
        "node_types": [
            "case",
            "entity",
            "evidence",
            "identifier",
            "infrastructure",
            "temporal",
        ],
        "source_occurrences_preserved": True,
        "review_bindings_preserved": True,
        "provenance_preserved": True,
        "source_records_mutated": False,
        "graph_record_created": False,
        "next_action": "review_cross_case_relationship_graph",
    }

    def build(**kwargs):
        captured.append(kwargs)
        return payload

    monkeypatch.setattr(routes, "build_cross_case_relationship_graph", build)

    client = _app(tmp_path, monkeypatch).test_client()
    assert client.get("/api/v1/cross-case-intelligence/graph").status_code == 401
    assert client.get("/cross-case-intelligence/graph").status_code in {302, 303}

    with client.session_transaction() as sess:
        sess["user"] = "analyst"
        sess["allowed_case_ids"] = ["case-alpha", "case-bravo"]

    ui = client.get("/cross-case-intelligence/graph")
    api = client.get("/api/v1/cross-case-intelligence/graph")

    assert ui.status_code == 200
    assert b"Cross-Case Relationship Graph" in ui.data
    assert b"Graph Summary" in ui.data
    assert b"Relationship Graph" in ui.data
    assert b"entity-42" in ui.data
    assert b"confirmed-link-1" in ui.data
    assert b"accepted-review bindings" in ui.data
    assert b"Viewing the graph creates no graph record" in ui.data
    assert api.status_code == 200
    assert api.get_json()["counts"]["nodes"] == 2
    assert api.get_json()["graph_sha256"] == "g" * 64
    assert all(
        call["allowed_case_ids"] == {"case-alpha", "case-bravo"} for call in captured
    )


def test_v25_3_registry_links_to_graph(tmp_path, monkeypatch):
    from src.socmint import cross_case_intelligence_routes_v25_0 as routes

    monkeypatch.setattr(
        routes,
        "build_confirmed_link_registry_workspace",
        lambda **kwargs: {
            "schema": "socmint.cross_case_confirmed_link_registry.v25_2",
            "version": "v25.2.0",
            "status": "ready",
            "access_scope": {"mode": "all_visible_cases", "allowed_case_ids": None},
            "confirmed_links": [],
            "confirmed_link_count": 0,
            "accepted_pending_registration": [],
            "accepted_pending_count": 0,
            "review_disposition_counts": {},
            "review_histories": {},
            "unreviewed_candidates_materialized": False,
            "rejected_deferred_split_history_retained": True,
            "source_records_mutated": False,
            "registry_record_created_by_view": False,
            "next_action": "review_confirmed_cross_case_links",
        },
    )
    client = _app(tmp_path, monkeypatch).test_client()
    with client.session_transaction() as sess:
        sess["user"] = "analyst"

    page = client.get("/cross-case-intelligence/confirmed-links")
    assert page.status_code == 200
    assert b"Open Relationship Graph" in page.data
    assert b"/cross-case-intelligence/graph" in page.data


def test_v25_3_release_note_client_and_no_migration():
    note = Path("release/V25_3_CROSS_CASE_RELATIONSHIP_GRAPH.md").read_text(
        encoding="utf-8"
    )
    script = Path(
        "src/socmint/static/cross_case_relationship_graph_v25_3.js"
    ).read_text(encoding="utf-8")
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v25_3*")
    ]

    assert (
        "cases, entities, identifiers, infrastructure, evidence, and temporal relationships"
        in note
    )
    assert "confirmed-link IDs" in note
    assert "source occurrences" in note
    assert "accepted-review bindings" in note
    assert "access scope" in note
    assert "provenance" in note
    assert "every node and edge" in note
    assert "read-only" in note
    assert "cross-case-relationship-graph-data" in script
    assert "edge_sha256" not in script
    assert migrations == []
