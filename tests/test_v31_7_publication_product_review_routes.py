from flask import Flask

from src.socmint.publication_product_review_routes_v31_7 import (
    register_publication_product_review_routes_v31_7,
)


def test_v31_7_product_review_routes_require_admin_and_report_ready(monkeypatch):
    app = Flask(__name__, template_folder="../src/socmint/templates")
    app.secret_key = "test-secret"
    app.add_url_rule("/login", "dashboard.login", lambda: "login")
    monkeypatch.setattr(
        "src.socmint.publication_product_review_routes_v31_7.actor_is_administrator",
        lambda actor: actor == "admin",
    )
    monkeypatch.setattr(
        "src.socmint.publication_product_review_routes_v31_7.build_publication_product_review",
        lambda **kwargs: {
            "status": "ready_for_browser_e2e",
            "ready": True,
            "blockers": [],
            "blocker_count": 0,
            "journey": [],
            "journey_step_count": 7,
            "module_checks": [],
            "asset_checks": [],
            "route_checks": [],
            "migration_artifacts": [],
        },
    )
    register_publication_product_review_routes_v31_7(app)
    client = app.test_client()

    assert client.get("/publication-review/product-review").status_code == 302
    assert client.get("/api/v1/publication-review/product-review-checkpoint").status_code == 401

    with client.session_transaction() as session:
        session["user"] = "viewer"
    assert client.get("/api/v1/publication-review/product-review-checkpoint").status_code == 403

    with client.session_transaction() as session:
        session["user"] = "admin"
    response = client.get("/api/v1/publication-review/product-review-checkpoint")
    assert response.status_code == 200
    assert response.get_json()["ready"] is True
