from flask import Flask

from src.socmint.delivery_attempt_receipt_ledger_routes_v32_4 import (
    register_delivery_attempt_receipt_ledger_routes_v32_4,
)


def test_v32_4_routes_require_admin_and_record_attempt(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "test-secret"
    monkeypatch.setattr(
        "src.socmint.delivery_attempt_receipt_ledger_routes_v32_4."
        "actor_is_administrator",
        lambda actor: actor == "admin",
    )
    monkeypatch.setattr(
        "src.socmint.delivery_attempt_receipt_ledger_routes_v32_4."
        "delivery_attempt_history",
        lambda: [],
    )
    monkeypatch.setattr(
        "src.socmint.delivery_attempt_receipt_ledger_routes_v32_4."
        "record_delivery_attempt",
        lambda **kwargs: {
            "status": "delivery_attempt_recorded",
            "delivery_attempt_id": "delivery-attempt-1",
        },
    )
    register_delivery_attempt_receipt_ledger_routes_v32_4(app)
    client = app.test_client()

    assert client.get(
        "/api/v1/dissemination-governance/delivery-attempts"
    ).status_code == 401

    with client.session_transaction() as current_session:
        current_session["user"] = "admin"
    response = client.post(
        "/api/v1/dissemination-governance/packages/package-1/delivery-attempts",
        json={
            "recipient_id": "recipient-1",
            "delivery_channel": "secure_portal",
            "endpoint_reference": "opaque-endpoint-token",
            "attempt_result": "accepted",
            "transport_reference": "transport-1",
            "reason": "authorized delivery",
            "confirmed": True,
        },
    )

    assert response.status_code == 201
    assert response.get_json()["delivery_attempt_id"] == "delivery-attempt-1"
