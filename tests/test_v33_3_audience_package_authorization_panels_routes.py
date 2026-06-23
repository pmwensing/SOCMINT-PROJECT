from flask import Flask

from src.socmint.audience_package_authorization_panels_routes_v33_3 import (
    register_audience_package_authorization_panels_routes_v33_3,
)


def test_v33_3_routes_require_admin_and_return_panels(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "test-secret"
    monkeypatch.setattr(
        "src.socmint.audience_package_authorization_panels_routes_v33_3."
        "actor_is_administrator",
        lambda actor: actor == "admin",
    )
    monkeypatch.setattr(
        "src.socmint.audience_package_authorization_panels_routes_v33_3."
        "build_case_audience_package_authorization_panels",
        lambda case_id: {
            "schema": "socmint.audience_package_authorization_panels.v33_3",
            "version": "v33.3.0",
            "status": "ready",
            "case_id": case_id,
            "panels": {
                "audience": {"panel": "audience"},
                "package": {"panel": "package"},
                "authorization": {"panel": "authorization"},
            },
        },
    )
    monkeypatch.setattr(
        "src.socmint.audience_package_authorization_panels_routes_v33_3."
        "build_case_governance_panel",
        lambda case_id, panel_name: {
            "schema": "socmint.audience_package_authorization_panels.v33_3",
            "version": "v33.3.0",
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
        "audience-package-authorization-panels"
    )
    assert response.status_code == 401

    with client.session_transaction() as current_session:
        current_session["user"] = "admin"

    response = client.get(
        "/api/v1/dissemination-governance/cases/case-1/"
        "audience-package-authorization-panels"
    )
    assert response.status_code == 200
    assert response.get_json()["panels"]["package"]["panel"] == "package"

    response = client.get(
        "/api/v1/dissemination-governance/cases/case-1/"
        "governance-panels/authorization"
    )
    assert response.status_code == 200
    assert response.get_json()["panel"] == "authorization"
    assert response.get_json()["read_only"] is True
