from flask import Flask

from src.socmint.dissemination_package_routes_v32_2 import (
    register_dissemination_package_routes_v32_2,
)


def test_v32_2_routes_require_admin_and_create_package(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "test-secret"
    monkeypatch.setattr(
        "src.socmint.dissemination_package_routes_v32_2.actor_is_administrator",
        lambda actor: actor == "admin",
    )
    monkeypatch.setattr(
        "src.socmint.dissemination_package_routes_v32_2.dissemination_package_history",
        lambda: [],
    )
    monkeypatch.setattr(
        "src.socmint.dissemination_package_routes_v32_2.assemble_dissemination_package",
        lambda **kwargs: {
            "status": "dissemination_package_assembled",
            "dissemination_package_id": "dissemination-package-1",
        },
    )
    register_dissemination_package_routes_v32_2(app)
    client = app.test_client()

    response = client.get("/api/v1/dissemination-governance/packages")
    assert response.status_code == 401

    with client.session_transaction() as current_session:
        current_session["user"] = "viewer"
    response = client.get("/api/v1/dissemination-governance/packages")
    assert response.status_code == 403

    with client.session_transaction() as current_session:
        current_session["user"] = "admin"
    response = client.post(
        "/api/v1/dissemination-governance/published-revisions/"
        "published-dossier-revision-1/audience-contracts/"
        "audience-contract-1/packages",
        json={
            "package_label": "Restricted Review Package",
            "reason": "operator request",
            "confirmed": True,
        },
    )

    assert response.status_code == 201
    assert response.get_json()["dissemination_package_id"] == "dissemination-package-1"
