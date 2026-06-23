from flask import Flask

from src.socmint.recipient_feedback_correction_intake_routes_v32_5 import (
    register_recipient_feedback_correction_intake_routes_v32_5,
)


def test_v32_5_routes_require_admin_and_record_feedback(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "test-secret"
    monkeypatch.setattr(
        "src.socmint.recipient_feedback_correction_intake_routes_v32_5."
        "actor_is_administrator",
        lambda actor: actor == "admin",
    )
    monkeypatch.setattr(
        "src.socmint.recipient_feedback_correction_intake_routes_v32_5."
        "recipient_feedback_history",
        lambda: [],
    )
    monkeypatch.setattr(
        "src.socmint.recipient_feedback_correction_intake_routes_v32_5."
        "record_recipient_feedback",
        lambda **kwargs: {
            "status": "recipient_feedback_recorded",
            "recipient_feedback_id": "recipient-feedback-1",
        },
    )
    register_recipient_feedback_correction_intake_routes_v32_5(app)
    client = app.test_client()

    response = client.get(
        "/api/v1/dissemination-governance/recipient-feedback"
    )
    assert response.status_code == 401

    with client.session_transaction() as current_session:
        current_session["user"] = "admin"
    response = client.post(
        "/api/v1/dissemination-governance/delivery-receipts/"
        "receipt-1/recipient-feedback",
        json={
            "feedback_type": "question",
            "severity": "low",
            "recipient_reference": "recipient-1",
            "summary": "Question",
            "detail": "Please clarify the finding.",
            "confirmed": True,
        },
    )

    assert response.status_code == 201
    assert response.get_json()["recipient_feedback_id"] == (
        "recipient-feedback-1"
    )
