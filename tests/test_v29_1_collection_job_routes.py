from pathlib import Path

from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import register_dossier_assembly_routes_v21_0


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    monkeypatch.setenv("SOCMINT_SECRET_KEY", "v29-1-route-test-secret-key-with-more-than-32-characters")
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def test_v29_1_routes_require_admin_and_dispatch(tmp_path, monkeypatch):
    from src.socmint import collection_job_routes_v29_1 as routes
    payload = {"schema":"socmint.collection_job_workspace.v29_1","version":"v29.1.0","status":"ready","states":[],"contracts":[],"contract_count":0,"state_counts":{},"retryable_contracts":[],"retryable_contract_count":0,"blocked_contracts":[],"blocked_contract_count":0,"unresolved_contracts":[],"unresolved_contract_count":0,"contract_findings":[],"contract_finding_count":0,"collection_job_history":[],"collection_job_event_count":0,"append_only":True,"legacy_scan_jobs_mutated":False,"connector_execution_available":False,"retry_execution_available":False,"case_access_scope_changed":False}
    monkeypatch.setattr(routes, "actor_is_administrator", lambda actor: actor == "admin")
    monkeypatch.setattr(routes, "build_collection_job_workspace", lambda: payload)
    monkeypatch.setattr(routes, "create_collection_job_contract", lambda **kwargs: {"status":"collection_job_contract_created","collection_job_id":"collection-job-1"})
    monkeypatch.setattr(routes, "transition_collection_job", lambda **kwargs: {"status":"collection_job_transitioned","to_state":kwargs["to_state"]})
    client = _app(tmp_path, monkeypatch).test_client()
    assert client.get("/api/v1/collection-operations/jobs").status_code == 401
    with client.session_transaction() as sess:
        sess["user"] = "viewer"
    assert client.get("/api/v1/collection-operations/jobs").status_code == 403
    csrf = "v29-1-csrf-token"
    with client.session_transaction() as sess:
        sess["user"] = "admin"
        sess["_csrf_token"] = csrf
    headers = {"X-CSRF-Token": csrf}
    assert client.get("/collection-operations/jobs").status_code == 200
    created = client.post("/api/v1/collection-operations/jobs", json={"connector":"demo","target_value":"alice","target_type":"username","authorization_binding":{"request_id":"request-1"},"purpose":"investigation","idempotency_key":"idem-1","reason":"create","confirmed":True}, headers=headers)
    binding = {"collection_job_id":"collection-job-1","policy_evaluation_id":"evaluation-1","policy_event_sha256":"sha-1","decision":"allow","allowed_by_policy_ids":["policy-1"],"denied_by_policy_ids":[]}
    transitioned = client.post("/api/v1/collection-operations/jobs/collection-job-1/transition", json={"to_state":"authorized","authorization_binding":binding,"reason":"authorize","confirmed":True}, headers=headers)
    denied = client.post("/api/v1/collection-operations/jobs/collection-job-1/transition", json={"to_state":"authorized","authorization_binding":{"decision":"deny"},"reason":"authorize","confirmed":True}, headers=headers)
    assert created.status_code == 200
    assert transitioned.status_code == 200
    assert denied.status_code == 422
    assert denied.get_json()["blockers"][0]["key"] == "allowing_collection_policy_evaluation_required"


def test_v29_1_release_note_and_no_migration():
    note = Path("release/V29_1_COLLECTION_JOB_CONTRACT_STATE_MACHINE.md").read_text(encoding="utf-8")
    for phrase in ("Collection Job Contract and State Machine","drafted","authorized","queued","running","completed","failed","blocked","cancelled","superseded","idempotency key","attempt number","authorization binding","failure category","retry eligibility","append-only","no connector execution","no legacy scan-job mutation","no migration"):
        assert phrase in note
    migrations = [path for directory in (Path("migrations"),Path("alembic")) if directory.exists() for path in directory.rglob("*v29_1*")]
    assert migrations == []
