from flask import Flask

from src.socmint.analytic_product_review_routes_v30_7 import (
    register_analytic_product_review_routes_v30_7,
)


def test_v30_7_routes_require_admin_and_return_checkpoint(monkeypatch):
    app = Flask(__name__, template_folder="../src/socmint/templates")
    app.secret_key = "test-secret"
    app.add_url_rule("/login", "dashboard.login", lambda: "login")
    monkeypatch.setattr(
        "src.socmint.analytic_product_review_routes_v30_7.actor_is_administrator",
        lambda actor: actor == "admin",
    )
    monkeypatch.setattr(
        "src.socmint.analytic_product_review_routes_v30_7.build_analytic_product_review",
        lambda **kwargs: {
            "status": "ready_for_browser_e2e",
            "ready": True,
            "blocker_count": 0,
            "blockers": [],
            "journey_step_count": 7,
            "module_checks": [],
            "asset_checks": [],
            "route_checks": [],
            "journey": [],
        },
    )
    register_analytic_product_review_routes_v30_7(app)
    client = app.test_client()

    assert client.get("/analytic-review/product-review").status_code == 302
    assert (
        client.get("/api/v1/analytic-review/product-review-checkpoint").status_code
        == 401
    )

    with client.session_transaction() as session:
        session["user"] = "viewer"
    assert (
        client.get("/api/v1/analytic-review/product-review-checkpoint").status_code
        == 403
    )

    with client.session_transaction() as session:
        session["user"] = "admin"
    response = client.get("/api/v1/analytic-review/product-review-checkpoint")
    assert response.status_code == 200
    assert response.get_json()["ready"] is True
