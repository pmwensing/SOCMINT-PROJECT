from flask import Flask

from src.socmint.authorization_policy_release_gate_routes_v32_3 import (
    register_authorization_policy_release_gate_routes_v32_3,
)


def test_v32_3_routes_require_admin_and_record_decision(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "test-secret"
    monkeypatch.setattr(
        "src.socmint.authorization_policy_release_gate_routes_v32_3."
        "actor_is_administrator",
        lambda actor: actor == "admin",
    )
    monkeypatch.setattr(
        "src.socmint.authorization_policy_release_gate_routes_v32_3."
        "authorization_decision_history",
        lambda: [],
    )
    monkeypatch.setattr(
        "src.socmint.authorization_policy_release_gate_routes_v32_3."
        "record_authorization_policy_decision",
        lambda **kwargs: {
            "status": "approved_for_delivery_attempt",
            "authorization_decision_id": "authorization-decision-1",
        },
    )
    register_authorization_policy_release_gate_routes_v32_3(app)
    client = app.test_client()

    response = client.get(
        "/api/v1/dissemination-governance/authorization-decisions"
    )
    assert response.status_code == 401

    with client.session_transaction() as current_session:
        current_session["user"] = "viewer"
    response = client.get(
        "/api/v1/dissemination-governance/authorization-decisions"
    )
    assert response.status_code == 403

    with client.session_transaction() as current_session:
        current_session["user"] = "admin"
    response = client.post(
        "/api/v1/dissemination-governance/packages/"
        "dissemination-package-1/authorization-decisions",
        json={
            "decision": "approve",
            "reason": "policy review complete",
            "confirmed": True,
        },
    )

    assert response.status_code == 201
    assert response.get_json()["authorization_decision_id"] == (
        "authorization-decision-1"
    )
