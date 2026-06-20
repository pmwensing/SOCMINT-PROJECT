from flask import Flask

from src.socmint.collection_product_review_routes_v29_7 import register_collection_product_review_routes_v29_7


def test_v29_7_product_review_routes_auth_and_ready(monkeypatch):
    app = Flask(__name__, template_folder="../src/socmint/templates")
    app.secret_key = "test-secret"
    app.add_url_rule("/login", "dashboard.login", lambda: "login")
    for rule in (
        "/collection-operations", "/api/v1/collection-operations", "/collection-operations/jobs", "/api/v1/collection-operations/jobs",
        "/collection-operations/policies", "/api/v1/collection-operations/policies", "/collection-operations/adapters", "/api/v1/collection-operations/adapters",
        "/collection-operations/evidence", "/api/v1/collection-operations/evidence", "/collection-operations/recovery", "/api/v1/collection-operations/recovery",
        "/collection-operations/quality", "/api/v1/collection-operations/quality",
    ):
        app.add_url_rule(rule, rule, lambda: "ok")
    monkeypatch.setattr("src.socmint.collection_product_review_routes_v29_7.actor_is_administrator", lambda actor: actor == "admin")
    register_collection_product_review_routes_v29_7(app)
    client = app.test_client()
    response = client.get("/collection-operations/product-review")
    assert response.status_code == 302
    response = client.get("/api/v1/collection-operations/product-review-checkpoint")
    assert response.status_code == 401
    with client.session_transaction() as session:
        session["user"] = "admin"
    response = client.get("/api/v1/collection-operations/product-review-checkpoint")
    assert response.status_code == 200
    assert response.get_json()["ready"] is True
