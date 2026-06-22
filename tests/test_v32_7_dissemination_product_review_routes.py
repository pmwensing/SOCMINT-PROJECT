from flask import Flask

from src.socmint.dissemination_product_review_routes_v32_7 import (
    register_dissemination_product_review_routes_v32_7,
)


def test_v32_7_checkpoint_route_requires_admin_and_returns_ready(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "test-secret"
    app.add_url_rule("/login", endpoint="dashboard.login", view_func=lambda: "login")
    monkeypatch.setattr(
        "src.socmint.dissemination_product_review_routes_v32_7."
        "actor_is_administrator",
        lambda actor: actor == "admin",
    )
    monkeypatch.setattr(
        "src.socmint.dissemination_product_review_routes_v32_7."
        "build_dissemination_product_review",
        lambda **kwargs: {
            "status": "ready_for_browser_e2e",
            "ready": True,
            "blockers": [],
        },
    )
    register_dissemination_product_review_routes_v32_7(app)
    client = app.test_client()

    response = client.get(
        "/api/v1/dissemination-governance/product-review-checkpoint"
    )
    assert response.status_code == 401

    with client.session_transaction() as current_session:
        current_session["user"] = "admin"
    response = client.get(
        "/api/v1/dissemination-governance/product-review-checkpoint"
    )

    assert response.status_code == 200
    assert response.get_json()["ready"] is True
