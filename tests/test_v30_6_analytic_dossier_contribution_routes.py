from flask import Flask

from src.socmint.analytic_dossier_contribution_routes_v30_6 import register_analytic_dossier_contribution_routes_v30_6


def test_v30_6_routes_require_admin_and_record(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "test-secret"
    monkeypatch.setattr("src.socmint.analytic_dossier_contribution_routes_v30_6.actor_is_administrator", lambda actor: actor == "admin")
    monkeypatch.setattr("src.socmint.analytic_dossier_contribution_routes_v30_6.current_contribution_decisions", lambda: [])
    monkeypatch.setattr("src.socmint.analytic_dossier_contribution_routes_v30_6.contributions_for_claim", lambda claim_id: [])
    monkeypatch.setattr(
        "src.socmint.analytic_dossier_contribution_routes_v30_6.review_dossier_contribution",
        lambda **kwargs: {
            "status": "analytic_dossier_contribution_reviewed",
            "claim_id": kwargs["claim_id"],
            "dossier_contribution_id": "contribution-1",
        },
    )
    register_analytic_dossier_contribution_routes_v30_6(app)
    client = app.test_client()

    path = "/api/v1/analytic-review/claims/claim-1/dossier-contributions"
    assert client.get(path).status_code == 401

    with client.session_transaction() as session:
        session["user"] = "viewer"
    assert client.get(path).status_code == 403

    with client.session_transaction() as session:
        session["user"] = "admin"
    response = client.post(path, json={"confirmed": True})
    assert response.status_code == 200
    assert response.get_json()["dossier_contribution_id"] == "contribution-1"
