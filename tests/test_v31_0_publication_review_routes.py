from flask import Flask

from src.socmint.publication_review_routes_v31_0 import register_publication_review_routes_v31_0


def test_v31_0_routes_require_admin_and_return_workspace(monkeypatch):
    app = Flask(__name__, template_folder="../src/socmint/templates")
    app.secret_key = "test-secret"
    app.add_url_rule("/login", "dashboard.login", lambda: "login")
    monkeypatch.setattr(
        "src.socmint.publication_review_routes_v31_0.actor_is_administrator",
        lambda actor: actor == "admin",
    )
    monkeypatch.setattr(
        "src.socmint.publication_review_routes_v31_0.build_publication_review_workspace",
        lambda: {
            "status": "ready",
            "publication_ready": True,
            "blockers": [],
            "blocker_count": 0,
        },
    )
    register_publication_review_routes_v31_0(app)
    client = app.test_client()

    assert client.get("/publication-review").status_code == 302
    assert client.get("/api/v1/publication-review").status_code == 401

    with client.session_transaction() as session:
        session["user"] = "viewer"
    assert client.get("/api/v1/publication-review").status_code == 403

    with client.session_transaction() as session:
        session["user"] = "admin"
    response = client.get("/api/v1/publication-review")
    assert response.status_code == 200
    assert response.get_json()["publication_ready"] is True
