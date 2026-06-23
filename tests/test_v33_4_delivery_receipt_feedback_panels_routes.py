from flask import Flask

from src.socmint.audience_package_authorization_panels_routes_v33_3 import (
    register_audience_package_authorization_panels_routes_v33_3,
)


def test_v33_4_routes_require_admin_and_dispatch_panels(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "test-secret"
    monkeypatch.setattr(
        "src.socmint.audience_package_authorization_panels_routes_v33_3."
        "actor_is_administrator",
        lambda actor: actor == "admin",
    )
    monkeypatch.setattr(
        "src.socmint.delivery_receipt_feedback_panels_routes_v33_4."
        "actor_is_administrator",
        lambda actor: actor == "admin",
    )
    monkeypatch.setattr(
        "src.socmint.delivery_receipt_feedback_panels_routes_v33_4."
        "build_case_delivery_receipt_feedback_panels",
        lambda case_id: {
            "schema": "socmint.delivery_receipt_feedback_panels.v33_4",
            "version": "v33.4.0",
            "status": "ready",
            "case_id": case_id,
            "panels": {"delivery": {"panel": "delivery"}},
        },
    )
    monkeypatch.setattr(
        "src.socmint.audience_package_authorization_panels_routes_v33_3."
        "build_case_delivery_receipt_feedback_panel",
        lambda case_id, panel_name: {
            "schema": "socmint.delivery_receipt_feedback_panels.v33_4",
            "version": "v33.4.0",
            "status": "ready",
            "case_id": case_id,
            "panel": panel_name,
            "read_only": True,
        },
    )
    register_audience_package_authorization_panels_routes_v33_3(app)
    client = app.test_client()

    response = client.get(
        "/api/v1/dissemination-governance/cases/case-1/"
        "delivery-receipt-feedback-panels"
    )
    assert response.status_code == 401

    with client.session_transaction() as current_session:
        current_session["user"] = "admin"

    response = client.get(
        "/api/v1/dissemination-governance/cases/case-1/"
        "delivery-receipt-feedback-panels"
    )
    assert response.status_code == 200
    assert response.get_json()["panels"]["delivery"]["panel"] == "delivery"

    response = client.get(
        "/api/v1/dissemination-governance/cases/case-1/"
        "governance-panels/feedback"
    )
    assert response.status_code == 200
    assert response.get_json()["panel"] == "feedback"
    assert response.get_json()["read_only"] is True
