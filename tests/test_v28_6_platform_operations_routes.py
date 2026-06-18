from pathlib import Path

from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import register_dossier_assembly_routes_v21_0


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    monkeypatch.setenv("SOCMINT_SECRET_KEY", "v28-6-route-test-secret-key-with-more-than-32-characters")
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def test_v28_6_routes_require_admin_and_dispatch(tmp_path, monkeypatch):
    from src.socmint import platform_operations_routes_v28_6 as routes
    payload = {"schema":"socmint.platform_health_jobs_operational_audit.v28_6","version":"v28.6.0","status":"ready","overall_status":"healthy","database_health":{"ready":True},"storage_health":{},"configuration_state":{},"job_health":{},"connector_run_health":{},"audit_log_continuity":{},"operational_incidents":[],"open_operational_incidents":[],"operational_incident_count":0,"open_operational_incident_count":0,"operational_findings":[],"operational_finding_count":0,"operational_history":[],"operational_event_count":0}
    monkeypatch.setattr(routes, "actor_is_administrator", lambda actor: actor == "admin")
    monkeypatch.setattr(routes, "build_platform_operations_workspace", lambda **kwargs: payload)
    monkeypatch.setattr(routes, "open_incident", lambda **kwargs: {"status":"operational_incident_opened","incident_id":"incident-1"})
    monkeypatch.setattr(routes, "acknowledge_incident", lambda *args, **kwargs: {"status":"operational_incident_acknowledged"})
    monkeypatch.setattr(routes, "resolve_incident", lambda *args, **kwargs: {"status":"operational_incident_resolved"})
    client = _app(tmp_path, monkeypatch).test_client()
    assert client.get("/api/v1/administration/operations").status_code == 401
    with client.session_transaction() as sess:
        sess["user"] = "viewer"
    assert client.get("/api/v1/administration/operations").status_code == 403
    csrf = "v28-6-csrf-token"
    with client.session_transaction() as sess:
        sess["user"] = "admin"
        sess["_csrf_token"] = csrf
    headers = {"X-CSRF-Token": csrf}
    assert client.get("/administration/operations").status_code == 200
    assert client.get("/api/v1/administration/operations?stale_after_hours=12").status_code == 200
    opened = client.post("/api/v1/administration/operations/incidents", json={"title":"Failure","severity":"high","component":"jobs","reason":"investigate","confirmed":True}, headers=headers)
    acknowledged = client.post("/api/v1/administration/operations/incidents/incident-1/acknowledge", json={"note":"working","reason":"ack","confirmed":True}, headers=headers)
    resolved = client.post("/api/v1/administration/operations/incidents/incident-1/resolve", json={"resolution":"fixed","reason":"close","confirmed":True}, headers=headers)
    assert [opened.status_code, acknowledged.status_code, resolved.status_code] == [200,200,200]


def test_v28_6_release_note_and_no_migration():
    note = Path("release/V28_6_PLATFORM_HEALTH_JOBS_OPERATIONAL_AUDIT.md").read_text(encoding="utf-8")
    for phrase in ("Platform Health, Jobs, and Operational Audit","database readiness","storage readiness","background-job health","failed and stalled work","connector-run continuity","configuration state","audit-log continuity","operational incidents","immutable operational history","administrator required","explicit confirmation","no job execution","no service restart","no configuration mutation","no migration"):
        assert phrase in note
    migrations = [path for directory in (Path("migrations"),Path("alembic")) if directory.exists() for path in directory.rglob("*v28_6*")]
    assert migrations == []
