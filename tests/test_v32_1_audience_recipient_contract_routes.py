from flask import Flask

from src.socmint.audience_recipient_contract_routes_v32_1 import (
    register_audience_recipient_contract_routes_v32_1,
)


def test_v32_1_routes_require_admin_and_create_contract(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "test-secret"
    monkeypatch.setattr(
        "src.socmint.audience_recipient_contract_routes_v32_1.actor_is_administrator",
        lambda actor: actor == "admin",
    )
    monkeypatch.setattr(
        "src.socmint.audience_recipient_contract_routes_v32_1.audience_contract_history",
        lambda: [],
    )
    monkeypatch.setattr(
        "src.socmint.audience_recipient_contract_routes_v32_1.record_audience_recipient_contract",
        lambda **kwargs: {
            "status": "audience_contract_recorded",
            "audience_contract_id": "audience-contract-1",
        },
    )
    register_audience_recipient_contract_routes_v32_1(app)
    client = app.test_client()

    assert (
        client.get(
            "/api/v1/dissemination-governance/audience-contracts"
        ).status_code
        == 401
    )

    with client.session_transaction() as session:
        session["user"] = "viewer"
    assert (
        client.get(
            "/api/v1/dissemination-governance/audience-contracts"
        ).status_code
        == 403
    )

    with client.session_transaction() as session:
        session["user"] = "admin"
    response = client.post(
        "/api/v1/dissemination-governance/cases/case-1/audience-contracts",
        json={
            "audience_name": "Restricted Review Audience",
            "audience_type": "regulatory",
            "dissemination_purpose": "case review",
            "classification": "restricted",
            "recipients": [
                {
                    "recipient_id": "recipient-1",
                    "display_name": "Review Team",
                    "organization": "Example Agency",
                    "role": "reviewer",
                    "recipient_type": "team",
                    "dissemination_purpose": "case review",
                    "max_classification": "restricted",
                    "allowed_channels": ["secure_portal"],
                }
            ],
            "reason": "operator request",
            "confirmed": True,
        },
    )

    assert response.status_code == 201
    assert response.get_json()["audience_contract_id"] == "audience-contract-1"
