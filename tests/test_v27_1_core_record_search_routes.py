from pathlib import Path

from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import register_dossier_assembly_routes_v21_0


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    monkeypatch.setenv("SOCMINT_SECRET_KEY", "v27-1-route-test-secret-key-with-more-than-32-characters")
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def _payload():
    return {
        "schema": "socmint.core_record_search.v27_1",
        "version": "v27.1.0", "status": "ready", "query": "entity-42",
        "record_types": ["case", "entity", "evidence", "finding"],
        "field_catalog": {"entity": ["entity_id", "name"]},
        "applied_filters": {"record_types": ["entity"], "case_ids": ["case-a"], "actors": ["alice"], "statuses": [], "limit": 50},
        "facets": {"record_type": {"entity": 1}, "case_id": {"case-a": 1}, "actor": {"alice": 1}, "status": {"unspecified": 1}},
        "results": [{"result_id": "r1", "record_type": "entity", "case_id": "case-a", "score": 205.0, "matched_terms": ["entity-42"], "field_matches": [{"field": "entity_id", "value": "entity-42", "exact": True, "phrase": True, "token_hits": ["entity-42"], "partial_hits": [], "field_score": 286.2}], "preview": {"fields": [{"field": "entity_id", "value": "entity-42", "matched": True}, {"field": "name", "value": "Example Person", "matched": False}], "field_count": 2, "matched_field_count": 1}, "actor": "alice", "status": "unspecified", "occurred_at": "2026-06-17T01:00:00+00:00", "links": {"primary": "/case-intelligence-review/case-a", "case": "/case-intelligence-review/case-a", "evidence": "/dossier-assembly/case-a"}}],
        "result_count": 1, "record_type_counts": {"entity": 1}, "visible_case_ids": ["case-a"],
        "search_sha256": "b" * 64, "access_scope": {"mode": "restricted", "allowed_case_ids": ["case-a"]},
        "read_only": True, "source_records_mutated": False, "search_record_created": False,
        "case_access_scope_changed": False, "relevance_is_not_confidence": True,
        "next_action": "refine_core_record_search",
    }


def test_v27_1_routes_require_login_scope_filters_and_render(tmp_path, monkeypatch):
    from src.socmint import core_record_search_routes_v27_1 as routes
    captured = []
    def build(query, **kwargs):
        captured.append((query, kwargs))
        return _payload()
    monkeypatch.setattr(routes, "build_core_record_search", build)
    client = _app(tmp_path, monkeypatch).test_client()
    assert client.get("/api/v1/global-search/core-records?q=entity-42").status_code == 401
    assert client.get("/global-search/core-records?q=entity-42").status_code in {302, 303}
    with client.session_transaction() as sess:
        sess["user"] = "paul"
        sess["allowed_case_ids"] = ["case-a"]
    query = "?q=entity-42&type=entity&case_ids=case-a&actors=alice&limit=50"
    ui = client.get("/global-search/core-records" + query)
    api = client.get("/api/v1/global-search/core-records" + query)
    assert ui.status_code == 200
    for phrase in (b"Case, Entity, Evidence, and Finding Search", b"Facets", b"Field-Aware Results", b"Example Person"):
        assert phrase in ui.data
    assert api.status_code == 200
    assert api.get_json()["result_count"] == 1
    expected = {"record_types": ["entity"], "case_ids": ["case-a"], "actors": ["alice"], "statuses": [], "allowed_case_ids": {"case-a"}, "limit": 50}
    assert captured == [("entity-42", expected), ("entity-42", expected)]


def test_v27_1_release_note_and_no_migration():
    note = Path("release/V27_1_CASE_ENTITY_EVIDENCE_FINDING_SEARCH.md").read_text(encoding="utf-8")
    for phrase in (
        "Case, Entity, Evidence, and Finding Search", "field-aware matching", "facets",
        "result previews", "exact and partial matches", "relevance is not confidence",
        "case access scope", "read-only", "no migration",
    ):
        assert phrase in note
    migrations = [
        path for directory in (Path("migrations"), Path("alembic")) if directory.exists()
        for path in directory.rglob("*v27_1*")
    ]
    assert migrations == []
