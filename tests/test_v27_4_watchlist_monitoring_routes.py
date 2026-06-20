from pathlib import Path

from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import (
    register_dossier_assembly_routes_v21_0,
)


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    monkeypatch.setenv(
        "SOCMINT_SECRET_KEY", "v27-4-route-test-secret-key-with-more-than-32-characters"
    )
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def test_v27_4_routes_require_login_csrf_and_dispatch(tmp_path, monkeypatch):
    from src.socmint import watchlist_monitoring_routes_v27_4 as routes

    monkeypatch.setattr(
        routes,
        "build_watchlist_workspace",
        lambda user: {
            "schema": "socmint.watchlist_monitoring.v27_4",
            "version": "v27.4.0",
            "status": "ready",
            "user_identity": user,
            "watchlists": [],
            "watchlist_count": 0,
            "active_watchlist_count": 0,
            "paused_watchlist_count": 0,
            "due_watchlist_count": 0,
            "notification_pending_count": 0,
            "monitoring_run_count": 0,
        },
    )
    monkeypatch.setattr(
        routes,
        "create_watchlist",
        lambda **kwargs: {"status": "watchlist_created", "watchlist_id": "watch-1"},
    )
    monkeypatch.setattr(
        routes,
        "set_watchlist_status",
        lambda *args, **kwargs: {
            "status": "watchlist_paused"
            if kwargs["status"] == "paused"
            else "watchlist_resumed"
        },
    )
    monkeypatch.setattr(
        routes,
        "run_watchlist_monitoring",
        lambda *args, **kwargs: {
            "status": "watchlist_monitoring_completed",
            "result_count": 1,
        },
    )
    client = _app(tmp_path, monkeypatch).test_client()
    assert client.get("/api/v1/global-search/watchlists").status_code == 401
    assert client.get("/global-search/watchlists").status_code in {302, 303}
    csrf = "v27-4-csrf-token"
    with client.session_transaction() as sess:
        sess["user"] = "alice"
        sess["allowed_case_ids"] = ["case-a"]
        sess["_csrf_token"] = csrf
    headers = {"X-CSRF-Token": csrf}
    assert client.get("/global-search/watchlists").status_code == 200
    created = client.post(
        "/api/v1/global-search/watchlists",
        json={
            "name": "Daily",
            "saved_view_id": "view-1",
            "cadence": "daily",
            "notification_rule": "any_change",
            "confirmed": True,
        },
        headers=headers,
    )
    paused = client.post(
        "/api/v1/global-search/watchlists/watch-1/pause",
        json={"reason": "hold", "confirmed": True},
        headers=headers,
    )
    resumed = client.post(
        "/api/v1/global-search/watchlists/watch-1/resume",
        json={"reason": "continue", "confirmed": True},
        headers=headers,
    )
    run = client.post(
        "/api/v1/global-search/watchlists/watch-1/run",
        json={"limit": 25},
        headers=headers,
    )
    assert [
        created.status_code,
        paused.status_code,
        resumed.status_code,
        run.status_code,
    ] == [200, 200, 200, 200]


def test_v27_4_release_note_and_no_migration():
    note = Path("release/V27_4_WATCHLISTS_SCHEDULED_SEARCH_MONITORING.md").read_text(
        encoding="utf-8"
    )
    for phrase in (
        "Watchlists and Scheduled Search Monitoring",
        "active saved views",
        "monitoring cadence",
        "immutable monitoring runs",
        "added and removed results",
        "result-set SHA-256",
        "notification rules",
        "current case access scope",
        "watchlists do not grant access",
        "append-only",
        "no migration",
    ):
        assert phrase in note
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v27_4*")
    ]
    assert migrations == []
