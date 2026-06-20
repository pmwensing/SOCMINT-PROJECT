from pathlib import Path

from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import (
    register_dossier_assembly_routes_v21_0,
)


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    monkeypatch.setenv(
        "SOCMINT_SECRET_KEY", "v27-6-route-test-secret-key-with-more-than-32-characters"
    )
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def _payload():
    return {
        "schema": "socmint.search_reporting_history_audit.v27_6",
        "version": "v27.6.0",
        "status": "ready",
        "events": [
            {
                "history_event_id": "v27-history-1",
                "family": "saved_view",
                "source_action": "saved_search_view_created",
                "event_type": "created",
                "actor": "alice",
                "occurred_at": "2026-06-17T01:00:00+00:00",
                "identifiers": {"saved_view_id": "view-1"},
                "event_counts": {
                    "section_count": None,
                    "result_count": None,
                    "added_count": None,
                    "removed_count": None,
                },
                "hashes": {"definition_sha256": "a" * 64},
                "direct_links": {
                    "saved_views": "/global-search/saved-views",
                    "watchlists": "/global-search/watchlists",
                    "reports": "/global-search/reports",
                    "advanced_search": "/global-search/advanced",
                },
            }
        ],
        "event_count": 1,
        "family_counts": {"saved_view": 1},
        "action_counts": {"saved_search_view_created": 1},
        "actor_counts": {"alice": 1},
        "current_state": {
            "saved_views": [],
            "watchlists": [],
            "reports": [],
            "report_packages": [],
        },
        "current_state_counts": {
            "saved_view_count": 0,
            "active_saved_view_count": 0,
            "watchlist_count": 0,
            "active_watchlist_count": 0,
            "report_count": 0,
            "active_report_count": 0,
            "report_package_count": 0,
        },
        "history_sha256": "b" * 64,
        "filters": {"families": ["saved_view"], "actors": ["alice"], "limit": 50},
        "read_only": True,
        "source_records_mutated": False,
        "history_events_mutated": False,
        "case_access_scope_changed": False,
        "next_action": "review_search_reporting_history",
    }


def test_v27_6_routes_require_login_parse_filters_and_render(tmp_path, monkeypatch):
    from src.socmint import search_reporting_history_audit_routes_v27_6 as routes

    captured = []

    def build(**kwargs):
        captured.append(kwargs)
        return _payload()

    monkeypatch.setattr(routes, "build_search_reporting_history_audit", build)
    client = _app(tmp_path, monkeypatch).test_client()
    assert client.get("/api/v1/global-search/history").status_code == 401
    assert client.get("/global-search/history").status_code in {302, 303}
    with client.session_transaction() as sess:
        sess["user"] = "alice"
    query = "?families=saved_view&actors=alice&limit=50"
    ui = client.get("/global-search/history" + query)
    api = client.get("/api/v1/global-search/history" + query)
    assert ui.status_code == 200
    for phrase in (
        b"Search, Watchlist, and Reporting History and Audit",
        b"Current State",
        b"Ordered Operational History",
        b"saved_search_view_created",
    ):
        assert phrase in ui.data
    assert api.status_code == 200
    assert api.get_json()["event_count"] == 1
    assert captured == [
        {"families": ["saved_view"], "actors": ["alice"], "limit": 50},
        {"families": ["saved_view"], "actors": ["alice"], "limit": 50},
    ]


def test_v27_6_release_note_and_no_migration():
    note = Path("release/V27_6_SEARCH_WATCHLIST_REPORTING_HISTORY_AUDIT.md").read_text(
        encoding="utf-8"
    )
    for phrase in (
        "Search, Watchlist, and Reporting History and Audit",
        "ordered operational history",
        "saved-view lifecycle",
        "watchlist monitoring",
        "report definitions and packages",
        "actors",
        "source bindings",
        "access scope",
        "event counts",
        "current projected state",
        "read-only",
        "underlying events remain unchanged",
        "no migration",
    ):
        assert phrase in note
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v27_6*")
    ]
    assert migrations == []
