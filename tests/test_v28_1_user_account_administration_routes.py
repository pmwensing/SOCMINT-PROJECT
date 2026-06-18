from pathlib import Path

from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import register_dossier_assembly_routes_v21_0


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    monkeypatch.setenv("SOCMINT_SECRET_KEY", "v28-1-route-test-secret-key-with-more-than-32-characters")
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def test_v28_1_routes_require_admin_csrf_and_dispatch(tmp_path, monkeypatch):
    from src.socmint import user_account_routes_v28_1 as routes
    payload = {"schema":"socmint.user_account_administration.v28_1","version":"v28.1.0","status":"ready","users":[],"user_count":0,"active_user_count":0,"suspended_user_count":0,"administrator_count":0,"roles":["viewer","analyst","reviewer","supervisor","admin"],"account_history":[],"account_event_count":0,"credentials_visible":False,"credential_hashes_visible":False,"case_access_scope_changed":False}
    monkeypatch.setattr(routes, "actor_is_administrator", lambda actor: actor == "admin")
    monkeypatch.setattr(routes, "build_user_account_workspace", lambda: payload)
    monkeypatch.setattr(routes, "provision_user", lambda **kwargs: {"status":"user_provisioned","user":{"username":"alice"}})
    monkeypatch.setattr(routes, "update_user", lambda *args, **kwargs: {"status":"user_updated","user":{"username":args[0]}})
    client = _app(tmp_path, monkeypatch).test_client()
    assert client.get("/api/v1/administration/users").status_code == 401
    with client.session_transaction() as sess:
        sess["user"] = "viewer"
    assert client.get("/api/v1/administration/users").status_code == 403
    csrf = "v28-1-csrf-token"
    with client.session_transaction() as sess:
        sess["user"] = "admin"
        sess["_csrf_token"] = csrf
    headers = {"X-CSRF-Token": csrf}
    assert client.get("/administration/users").status_code == 200
    assert client.get("/api/v1/administration/users").status_code == 200
    created = client.post("/api/v1/administration/users", json={"username":"alice","role":"analyst","reason":"new user","confirmed":True}, headers=headers)
    activated = client.post("/api/v1/administration/users/alice/activate", json={"reason":"ready","confirmed":True}, headers=headers)
    suspended = client.post("/api/v1/administration/users/alice/suspend", json={"reason":"leave","confirmed":True}, headers=headers)
    updated = client.post("/api/v1/administration/users/alice/update", json={"role":"reviewer","reason":"promotion","confirmed":True}, headers=headers)
    assert [created.status_code,activated.status_code,suspended.status_code,updated.status_code] == [200,200,200,200]


def test_v28_1_release_note_and_no_migration():
    note = Path("release/V28_1_USER_ACCOUNT_ADMINISTRATION.md").read_text(encoding="utf-8")
    for phrase in ("User and Account Administration","account provisioning","activation","suspension","role updates","administrator required","explicit confirmation","administrative reason","immutable account audit history","last active administrator","credentials are never returned","case access scope is unchanged","no migration"):
        assert phrase in note
    migrations = [path for directory in (Path("migrations"),Path("alembic")) if directory.exists() for path in directory.rglob("*v28_1*")]
    assert migrations == []
