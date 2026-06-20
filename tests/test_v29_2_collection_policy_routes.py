from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import (
    register_dossier_assembly_routes_v21_0,
)


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    monkeypatch.setenv(
        "SOCMINT_SECRET_KEY", "v29-2-route-test-secret-key-with-more-than-32-characters"
    )
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def test_v29_2_routes_require_admin_and_dispatch(tmp_path, monkeypatch):
    from src.socmint import collection_policy_routes_v29_2 as routes

    payload = {
        "status": "ready",
        "policies": [],
        "active_policies": [],
        "policy_count": 0,
        "active_policy_count": 0,
        "expired_policies": [],
        "expired_policy_count": 0,
        "review_due_policies": [],
        "review_due_policy_count": 0,
        "evaluations": [],
        "evaluation_count": 0,
        "evaluation_decision_counts": {},
        "policy_findings": [],
        "policy_finding_count": 0,
        "collection_policy_history": [],
        "collection_policy_event_count": 0,
    }
    monkeypatch.setattr(
        routes, "actor_is_administrator", lambda actor: actor == "admin"
    )
    monkeypatch.setattr(
        routes, "build_collection_policy_workspace", lambda **kwargs: payload
    )
    monkeypatch.setattr(
        routes,
        "create_collection_policy",
        lambda **kwargs: {
            "status": "collection_policy_created",
            "policy_id": "policy-1",
        },
    )
    monkeypatch.setattr(
        routes,
        "revise_collection_policy",
        lambda *args, **kwargs: {
            "status": "collection_policy_revised",
            "policy_id": "policy-2",
        },
    )
    monkeypatch.setattr(
        routes,
        "evaluate_collection_job_policy",
        lambda **kwargs: {
            "status": "collection_policy_evaluated",
            "policy_evaluation_id": "evaluation-1",
            "policy_event_sha256": "sha-1",
            "evaluation": {
                "decision": "allow",
                "allowed_by_policy_ids": ["policy-1"],
                "denied_by_policy_ids": [],
            },
        },
    )
    client = _app(tmp_path, monkeypatch).test_client()
    assert client.get("/api/v1/collection-operations/policies").status_code == 401
    with client.session_transaction() as sess:
        sess["user"] = "viewer"
    assert client.get("/api/v1/collection-operations/policies").status_code == 403
    csrf = "v29-2-csrf-token"
    with client.session_transaction() as sess:
        sess["user"] = "admin"
        sess["_csrf_token"] = csrf
    headers = {"X-CSRF-Token": csrf}
    assert client.get("/collection-operations/policies").status_code == 200
    assert client.get("/api/v1/collection-operations/policies").status_code == 200
    created = client.post(
        "/api/v1/collection-operations/policies",
        json={"name": "Policy", "reason": "define", "confirmed": True},
        headers=headers,
    )
    revised = client.post(
        "/api/v1/collection-operations/policies/policy-1/revise",
        json={
            "definition": {"name": "Policy v2"},
            "reason": "revise",
            "confirmed": True,
        },
        headers=headers,
    )
    evaluated = client.post(
        "/api/v1/collection-operations/jobs/collection-job-1/evaluate-policy",
        json={"jurisdiction": "CA", "reason": "evaluate", "confirmed": True},
        headers=headers,
    )
    assert [created.status_code, revised.status_code, evaluated.status_code] == [
        200,
        200,
        200,
    ]
    assert evaluated.get_json()["authorization_binding"]["decision"] == "allow"
