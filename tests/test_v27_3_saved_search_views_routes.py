from pathlib import Path

from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import register_dossier_assembly_routes_v21_0


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    monkeypatch.setenv("SOCMINT_SECRET_KEY", "v27-3-route-test-secret-key-with-more-than-32-characters")
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def test_v27_3_routes_require_login_and_dispatch(tmp_path, monkeypatch):
    from src.socmint import saved_search_views_routes_v27_3 as routes
    monkeypatch.setattr(routes, "build_saved_views_workspace", lambda user: {"schema":"socmint.saved_search_views.v27_3","version":"v27.3.0","status":"ready","user_identity":user,"visibilities":["private","shared"],"saved_views":[],"active_saved_views":[],"owned_saved_views":[],"shared_saved_views":[],"saved_view_count":0,"active_saved_view_count":0,"owned_saved_view_count":0,"shared_saved_view_count":0,"history_count":0})
    monkeypatch.setattr(routes, "create_view", lambda **kwargs: {"status":"saved_view_created","saved_view_id":"view-1"})
    monkeypatch.setattr(routes, "revise_view", lambda *args, **kwargs: {"status":"saved_view_revised","saved_view_id":"view-2"})
    monkeypatch.setattr(routes, "deactivate_view", lambda *args, **kwargs: {"status":"saved_view_deactivated"})
    monkeypatch.setattr(routes, "run_saved_view", lambda *args, **kwargs: {"status":"saved_view_executed","execution":{"result_count":0}})
    client = _app(tmp_path, monkeypatch).test_client()
    assert client.get("/api/v1/global-search/saved-views").status_code == 401
    assert client.get("/global-search/saved-views").status_code in {302,303}
    csrf = "v27-3-test-csrf-token"
    with client.session_transaction() as sess:
        sess["user"] = "alice"
        sess["allowed_case_ids"] = ["case-a"]
        sess["_csrf_token"] = csrf
    headers = {"X-CSRF-Token": csrf}
    assert client.get("/global-search/saved-views").status_code == 200
    created = client.post("/api/v1/global-search/saved-views", json={"name":"Preset","query":"alpha","filters":{},"visibility":"private","confirmed":True}, headers=headers)
    revised = client.post("/api/v1/global-search/saved-views/view-1/revise", json={"name":"Preset 2","query":"alpha","filters":{},"visibility":"shared","reason":"update","confirmed":True}, headers=headers)
    deactivated = client.post("/api/v1/global-search/saved-views/view-2/deactivate", json={"reason":"obsolete","confirmed":True}, headers=headers)
    executed = client.get("/api/v1/global-search/saved-views/view-2/run?limit=25")
    assert [created.status_code,revised.status_code,deactivated.status_code,executed.status_code] == [200,200,200,200]


def test_v27_3_release_note_and_no_migration():
    note = Path("release/V27_3_SAVED_VIEWS_SEARCH_PRESETS.md").read_text(encoding="utf-8")
    for phrase in ("Saved Views and Search Presets","named query and filter definitions","immutable revisions","private and shared visibility","duplicate-safe naming","current case access scope","saved views do not grant access","append-only","no migration"):
        assert phrase in note
    migrations = [path for directory in (Path("migrations"),Path("alembic")) if directory.exists() for path in directory.rglob("*v27_3*")]
    assert migrations == []
