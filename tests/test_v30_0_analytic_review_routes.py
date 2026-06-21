from flask import Flask

from src.socmint.analytic_review_routes_v30_0 import (
    register_analytic_review_routes_v30_0,
)


def test_v30_0_routes_require_admin_and_return_workspace(monkeypatch):
    app = Flask(__name__, template_folder="../src/socmint/templates")
    app.secret_key = "test-secret"
    app.add_url_rule("/login", "dashboard.login", lambda: "login")
    monkeypatch.setattr(
        "src.socmint.analytic_review_routes_v30_0.actor_is_administrator",
        lambda actor: actor == "admin",
    )
    monkeypatch.setattr(
        "src.socmint.analytic_review_routes_v30_0.build_analytic_review_workspace",
        lambda: {
            "status": "ready",
            "read_only": True,
            "evidence_inventory": [],
            "observation_inventory": [],
            "claim_inventory": [],
            "confidence_inventory": [],
            "review_item_inventory": [],
            "review_decision_inventory": [],
            "contradiction_inventory": [],
            "dossier_contribution_inventory": [],
            "analytic_findings": [],
        },
    )
    register_analytic_review_routes_v30_0(app)
    client = app.test_client()

    assert client.get("/analytic-review").status_code == 302
    assert client.get("/api/v1/analytic-review").status_code == 401

    with client.session_transaction() as session:
        session["user"] = "analyst"
    assert client.get("/api/v1/analytic-review").status_code == 403

    with client.session_transaction() as session:
        session["user"] = "admin"
    response = client.get("/api/v1/analytic-review")
    assert response.status_code == 200
    assert response.get_json()["read_only"] is True
