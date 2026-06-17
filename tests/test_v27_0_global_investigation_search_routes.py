from pathlib import Path

from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import register_dossier_assembly_routes_v21_0


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    monkeypatch.setenv("SOCMINT_SECRET_KEY", "v27-route-test-secret-key-with-more-than-32-characters")
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def _payload():
    return {
        "schema": "socmint.global_investigation_search.v27_0",
        "version": "v27.0.0", "status": "ready", "query": "entity-42",
        "query_contract": {"query": "entity-42", "tokens": ["entity-42"], "result_types": [], "limit": 100},
        "result_types": ["case", "entity", "evidence"],
        "results": [{"result_id": "r1", "result_type": "entity", "case_id": "case-a", "title": "Example Person", "summary": "active", "score": 72.0, "matched_terms": ["entity-42"], "actor": "alice", "occurred_at": "2026-06-17T01:00:00+00:00", "links": {"primary": "/case-intelligence-review/case-a", "case": "/case-intelligence-review/case-a", "evidence": "/dossier-assembly/case-a"}}],
        "result_count": 1, "result_type_counts": {"entity": 1}, "visible_case_ids": ["case-a"],
        "access_scope": {"mode": "restricted", "allowed_case_ids": ["case-a"]},
        "search_sha256": "a" * 64, "read_only": True, "source_records_mutated": False,
        "search_record_created": False, "case_access_scope_changed": False,
        "next_action": "refine_global_investigation_search",
    }


def test_v27_0_routes_require_login_scope_and_render(tmp_path, monkeypatch):
    from src.socmint import global_investigation_search_routes_v27_0 as routes
    captured = []
    def build(query, **kwargs):
        captured.append((query, kwargs))
        return _payload()
    monkeypatch.setattr(routes, "build_global_investigation_search", build)
    client = _app(tmp_path, monkeypatch).test_client()
    assert client.get("/api/v1/global-search?q=entity-42").status_code == 401
    assert client.get("/global-search?q=entity-42").status_code in {302, 303}
    with client.session_transaction() as sess:
        sess["user"] = "paul"
        sess["allowed_case_ids"] = ["case-a"]
    ui = client.get("/global-search?q=entity-42&limit=50")
    api = client.get("/api/v1/global-search?q=entity-42&limit=50")
    assert ui.status_code == 200
    for phrase in (b"Global Investigation Search", b"Search Summary", b"Normalized Results", b"Example Person"):
        assert phrase in ui.data
    assert api.status_code == 200
    assert api.get_json()["result_count"] == 1
    assert captured == [
        ("entity-42", {"result_types": [], "allowed_case_ids": {"case-a"}, "limit": 50}),
        ("entity-42", {"result_types": [], "allowed_case_ids": {"case-a"}, "limit": 50}),
    ]


def test_v27_0_release_note_and_no_migration():
    note = Path("release/V27_0_GLOBAL_INVESTIGATION_SEARCH.md").read_text(encoding="utf-8")
    for phrase in (
        "Global Investigation Search", "cases, entities, identifiers, infrastructure, evidence, findings",
        "case access scope", "normalized results", "ranking metadata", "direct links", "read-only",
    ):
        assert phrase in note
    migrations = [
        path for directory in (Path("migrations"), Path("alembic")) if directory.exists()
        for path in directory.rglob("*v27_0*")
    ]
    assert migrations == []
