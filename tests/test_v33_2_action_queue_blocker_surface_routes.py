from flask import Flask

from src.socmint.action_queue_blocker_surface_routes_v33_2 import (
    register_action_queue_blocker_surface_routes_v33_2,
)


def test_v33_2_routes_require_admin_and_return_queue(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "test-secret"
    monkeypatch.setattr(
        "src.socmint.action_queue_blocker_surface_routes_v33_2."
        "actor_is_administrator",
        lambda actor: actor == "admin",
    )
    monkeypatch.setattr(
        "src.socmint.action_queue_blocker_surface_routes_v33_2."
        "build_case_action_queue",
        lambda case_id: {
            "schema": "socmint.action_queue_blocker_surface.v33_2",
            "version": "v33.2.0",
            "status": "attention_required",
            "case_id": case_id,
            "action_queue": [{"action": "record_retention_decision"}],
            "blockers": [{"key": "retention_decision_required"}],
            "read_only": True,
        },
    )
    register_action_queue_blocker_surface_routes_v33_2(app)
    client = app.test_client()

    response = client.get(
        "/api/v1/dissemination-governance/cases/case-1/action-queue"
    )
    assert response.status_code == 401

    with client.session_transaction() as current_session:
        current_session["user"] = "viewer"
    response = client.get(
        "/api/v1/dissemination-governance/cases/case-1/action-queue"
    )
    assert response.status_code == 403

    with client.session_transaction() as current_session:
        current_session["user"] = "admin"
    response = client.get(
        "/api/v1/dissemination-governance/cases/case-1/action-queue"
    )
    assert response.status_code == 200
    assert response.get_json()["action_queue"][0]["action"] == (
        "record_retention_decision"
    )

    response = client.get(
        "/api/v1/dissemination-governance/cases/case-1/blockers"
    )
    assert response.status_code == 200
    assert response.get_json()["read_only"] is True
