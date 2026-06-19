from pathlib import Path

from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import register_dossier_assembly_routes_v21_0


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    monkeypatch.setenv("SOCMINT_SECRET_KEY", "v29-5-route-test-secret-key-with-more-than-32-characters")
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def test_v29_5_routes_require_admin_and_dispatch(tmp_path, monkeypatch):
    from src.socmint import recovery_operations_routes_v29_5 as routes
    payload = {"status":"ready","retry_requests":[],"retry_request_count":0,"retry_request_state_counts":{},"pending_retry_requests":[],"pending_retry_request_count":0,"approved_retry_requests":[],"approved_retry_request_count":0,"retry_window_open":[],"retry_window_open_count":0,"retry_window_expired":[],"retry_window_expired_count":0,"recovery_plans":[],"recovery_plan_count":0,"operator_interventions":[],"operator_intervention_count":0,"recovery_findings":[],"recovery_finding_count":0,"recovery_history":[],"recovery_event_count":0}
    monkeypatch.setattr(routes, "actor_is_administrator", lambda actor: actor == "admin")
    monkeypatch.setattr(routes, "build_recovery_operations_workspace", lambda: payload)
    monkeypatch.setattr(routes, "request_retry", lambda **kwargs: {"status":"collection_retry_requested","retry_request_id":"retry-1"})
    monkeypatch.setattr(routes, "decide_retry", lambda **kwargs: {"status":"collection_retry_decided","approved":kwargs["approved"]})
    monkeypatch.setattr(routes, "create_recovery_plan", lambda **kwargs: {"status":"collection_recovery_plan_created","recovery_plan_id":"plan-1"})
    monkeypatch.setattr(routes, "record_operator_intervention", lambda **kwargs: {"status":"collection_operator_intervention_recorded","operator_intervention_id":"intervention-1"})
    client = _app(tmp_path, monkeypatch).test_client()
    assert client.get("/api/v1/collection-operations/recovery").status_code == 401
    with client.session_transaction() as sess:
        sess["user"] = "viewer"
    assert client.get("/api/v1/collection-operations/recovery").status_code == 403
    csrf = "v29-5-csrf-token"
    with client.session_transaction() as sess:
        sess["user"] = "admin"
        sess["_csrf_token"] = csrf
    headers = {"X-CSRF-Token": csrf}
    assert client.get("/collection-operations/recovery").status_code == 200
    assert client.get("/api/v1/collection-operations/recovery").status_code == 200
    requested = client.post("/api/v1/collection-operations/jobs/job-1/retry-requests", json={"idempotency_key":"retry-1","backoff_seconds":30,"max_attempts":3,"reason":"retry","confirmed":True}, headers=headers)
    decided = client.post("/api/v1/collection-operations/retry-requests/retry-1/decision", json={"approved":True,"decision_reason":"transient","confirmed":True}, headers=headers)
    planned = client.post("/api/v1/collection-operations/jobs/job-1/recovery-plans", json={"retry_request_id":"retry-1","plan_type":"retry","steps":["wait","requeue"],"operator_required":True,"reason":"plan","confirmed":True}, headers=headers)
    intervened = client.post("/api/v1/collection-operations/jobs/job-1/interventions", json={"intervention_type":"manual_review","resolution":"reviewed","reason":"operator review","confirmed":True}, headers=headers)
    assert [requested.status_code,decided.status_code,planned.status_code,intervened.status_code] == [200,200,200,200]


def test_v29_5_release_note_and_no_migration():
    note = Path("release/V29_5_RETRY_RECOVERY_OPERATOR_INTERVENTION.md").read_text(encoding="utf-8")
    for phrase in ("Retry, Recovery, and Operator Intervention","retry requests","retry approvals","idempotency key","backoff","retry window","maximum attempts","recovery plans","operator intervention","blocked-state resolution","manual cancellation","supersession","append-only recovery history","no automatic connector execution","no migration"):
        assert phrase in note
    migrations = [path for directory in (Path("migrations"),Path("alembic")) if directory.exists() for path in directory.rglob("*v29_5*")]
    assert migrations == []
