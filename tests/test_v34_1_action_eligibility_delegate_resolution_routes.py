from flask import Flask

from src.socmint.action_eligibility_delegate_resolution_routes_v34_1 import (
    register_action_eligibility_delegate_resolution_routes_v34_1,
)


def test_v34_1_route_requires_admin_and_returns_resolution(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "test-secret"
    monkeypatch.setattr(
        "src.socmint.action_eligibility_delegate_resolution_routes_v34_1."
        "actor_is_administrator",
        lambda actor: actor == "admin",
    )
    monkeypatch.setattr(
        "src.socmint.action_eligibility_delegate_resolution_routes_v34_1."
        "build_action_eligibility_delegate_resolution",
        lambda case_id: {
            "schema": "socmint.action_eligibility_delegate_resolution.v34_1",
            "version": "v34.1.0",
            "status": "ready_for_confirmation",
            "case_id": case_id,
            "eligible_count": 1,
            "blocked_count": 0,
            "resolutions": [
                {
                    "action": "record_retention_decision",
                    "eligible": True,
                    "execution_performed": False,
                }
            ],
            "read_only": True,
        },
    )
    register_action_eligibility_delegate_resolution_routes_v34_1(app)
    client = app.test_client()
    route = (
        "/api/v1/dissemination-governance/cases/case-1/"
        "action-eligibility"
    )

    assert client.get(route).status_code == 401

    with client.session_transaction() as current_session:
        current_session["user"] = "viewer"
    assert client.get(route).status_code == 403

    with client.session_transaction() as current_session:
        current_session["user"] = "admin"
    response = client.get(route)

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["case_id"] == "case-1"
    assert payload["resolutions"][0]["eligible"] is True
    assert payload["resolutions"][0]["execution_performed"] is False
