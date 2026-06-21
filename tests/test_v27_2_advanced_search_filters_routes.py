from pathlib import Path

from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import (
    register_dossier_assembly_routes_v21_0,
)


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    monkeypatch.setenv(
        "SOCMINT_SECRET_KEY", "v27-2-route-test-secret-key-with-more-than-32-characters"
    )
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def _payload():
    return {
        "schema": "socmint.advanced_search_filters.v27_2",
        "version": "v27.2.0",
        "status": "ready",
        "query": "alpha",
        "sort_modes": ["relevance", "newest", "oldest", "case", "type", "actor"],
        "active_filters": {
            "record_types": ["case"],
            "case_ids": ["case-a"],
            "actors": ["alice"],
            "statuses": ["active"],
            "stages": ["review"],
            "source_actions": ["portfolio_case"],
            "confidences": [],
            "priorities": ["high"],
            "date_from": "2026-06-01",
            "date_to": "2026-06-30",
            "include_terms": ["alpha"],
            "exclude_terms": [],
            "exact_fields": {"case_id": "case-a"},
            "sort": "newest",
            "limit": 50,
        },
        "active_filter_count": 9,
        "facets": {
            "record_type": {"case": 1},
            "case_id": {"case-a": 1},
            "actor": {"alice": 1},
            "status": {"active": 1},
            "stage": {"review": 1},
            "source_action": {"portfolio_case": 1},
            "confidence": {"unspecified": 1},
            "priority": {"high": 1},
        },
        "filtered_facets": {"record_type": {"case": 1}},
        "excluded_counts": {},
        "candidate_count": 1,
        "result_count": 1,
        "results": [
            {
                "result_id": "r1",
                "record_type": "case",
                "case_id": "case-a",
                "score": 10.0,
                "actor": "alice",
                "status": "active",
                "occurred_at": "2026-06-10T10:00:00+00:00",
                "links": {"primary": "/case-a", "case": "/case-a"},
            }
        ],
        "filter_sha256": "a" * 64,
        "result_set_sha256": "b" * 64,
        "access_scope": {"mode": "restricted", "allowed_case_ids": ["case-a"]},
        "read_only": True,
        "source_records_mutated": False,
        "filter_record_created": False,
        "case_access_scope_changed": False,
        "relevance_is_not_confidence": True,
        "next_action": "review_filtered_results",
    }


def test_v27_2_routes_require_login_parse_filters_and_render(tmp_path, monkeypatch):
    from src.socmint import advanced_search_filters_routes_v27_2 as routes

    captured = []

    def build(query, **kwargs):
        captured.append((query, kwargs))
        return _payload()

    monkeypatch.setattr(routes, "build_advanced_search_filters", build)
    client = _app(tmp_path, monkeypatch).test_client()
    assert client.get("/api/v1/global-search/advanced?q=alpha").status_code == 401
    assert client.get("/global-search/advanced?q=alpha").status_code in {302, 303}
    with client.session_transaction() as sess:
        sess["user"] = "paul"
        sess["allowed_case_ids"] = ["case-a"]
    query = "?q=alpha&type=case&case_ids=case-a&actors=alice&statuses=active&stages=review&source_actions=portfolio_case&priorities=high&date_from=2026-06-01&date_to=2026-06-30&include_terms=alpha&field.case_id=case-a&sort=newest&limit=50"
    ui = client.get("/global-search/advanced" + query)
    api = client.get("/api/v1/global-search/advanced" + query)
    assert ui.status_code == 200
    for phrase in (
        b"Advanced Filters and Search Facets",
        b"Filter Summary",
        b"Available Facets",
        b"Filtered Results",
    ):
        assert phrase in ui.data
    assert api.status_code == 200
    assert api.get_json()["result_count"] == 1
    assert len(captured) == 2
    for query_value, kwargs in captured:
        assert query_value == "alpha"
        assert kwargs["record_types"] == ["case"]
        assert kwargs["case_ids"] == ["case-a"]
        assert kwargs["actors"] == ["alice"]
        assert kwargs["statuses"] == ["active"]
        assert kwargs["stages"] == ["review"]
        assert kwargs["source_actions"] == ["portfolio_case"]
        assert kwargs["priorities"] == ["high"]
        assert kwargs["exact_fields"] == {"case_id": "case-a"}
        assert kwargs["allowed_case_ids"] == {"case-a"}
        assert kwargs["limit"] == 50


def test_v27_2_release_note_and_no_migration():
    note = Path("release/V27_2_ADVANCED_FILTERS_SEARCH_FACETS.md").read_text(
        encoding="utf-8"
    )
    for phrase in (
        "Advanced Filters and Search Facets",
        "date windows",
        "include and exclude terms",
        "exact field constraints",
        "sort modes",
        "facet counts",
        "filter SHA-256",
        "case access scope",
        "relevance is not confidence",
        "read-only",
        "no migration",
    ):
        assert phrase in note
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v27_2*")
    ]
    assert migrations == []
