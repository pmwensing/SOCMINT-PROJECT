from flask import Flask

from src.socmint.recall_retention_lifecycle_routes_v32_6 import (
    register_recall_retention_lifecycle_routes_v32_6,
)


def test_v32_6_routes_require_admin_and_record_recall(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "test-secret"
    monkeypatch.setattr(
        "src.socmint.recall_retention_lifecycle_routes_v32_6."
        "actor_is_administrator",
        lambda actor: actor == "admin",
    )
    monkeypatch.setattr(
        "src.socmint.recall_retention_lifecycle_routes_v32_6."
        "record_recall_decision",
        lambda **kwargs: {
            "status": "recall_decision_recorded",
            "recall_decision_id": "recall-decision-1",
        },
    )
    register_recall_retention_lifecycle_routes_v32_6(app)
    client = app.test_client()

    response = client.get(
        "/api/v1/dissemination-governance/recall-decisions"
    )
    assert response.status_code == 401

    with client.session_transaction() as current_session:
        current_session["user"] = "admin"
    response = client.post(
        "/api/v1/dissemination-governance/correction-intakes/"
        "correction-1/recall-decisions",
        json={
            "decision": "initiate",
            "reason": "critical correction",
            "confirmed": True,
        },
    )

    assert response.status_code == 201
    assert response.get_json()["recall_decision_id"] == "recall-decision-1"


def test_v32_6_routes_record_retention_and_return_lifecycle(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "test-secret"
    monkeypatch.setattr(
        "src.socmint.recall_retention_lifecycle_routes_v32_6."
        "actor_is_administrator",
        lambda actor: actor == "admin",
    )
    monkeypatch.setattr(
        "src.socmint.recall_retention_lifecycle_routes_v32_6."
        "record_retention_decision",
        lambda **kwargs: {
            "status": "retention_decision_recorded",
            "retention_decision_id": "retention-decision-1",
        },
    )
    monkeypatch.setattr(
        "src.socmint.recall_retention_lifecycle_routes_v32_6."
        "lifecycle_history",
        lambda case_id=None: [{"case_id": case_id, "lifecycle_stage": "retention_decision"}],
    )
    monkeypatch.setattr(
        "src.socmint.recall_retention_lifecycle_routes_v32_6."
        "lifecycle_snapshot",
        lambda case_id: {"case_id": case_id, "event_count": 1},
    )
    register_recall_retention_lifecycle_routes_v32_6(app)
    client = app.test_client()
    with client.session_transaction() as current_session:
        current_session["user"] = "admin"

    response = client.post(
        "/api/v1/dissemination-governance/cases/case-1/retention-decisions",
        json={
            "disposition": "retain",
            "policy_id": "policy-7y",
            "reason": "required retention",
            "confirmed": True,
        },
    )
    assert response.status_code == 201

    response = client.get(
        "/api/v1/dissemination-governance/cases/case-1/lifecycle-history"
    )
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["snapshot"]["event_count"] == 1
    assert payload["lifecycle_history"][0]["case_id"] == "case-1"
