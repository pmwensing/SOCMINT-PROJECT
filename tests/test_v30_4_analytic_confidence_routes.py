from flask import Flask

from src.socmint.analytic_confidence_routes_v30_4 import register_analytic_confidence_routes_v30_4


def test_v30_4_routes_require_admin_and_assess(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "test-secret"
    monkeypatch.setattr("src.socmint.analytic_confidence_routes_v30_4.actor_is_administrator", lambda actor: actor == "admin")
    monkeypatch.setattr("src.socmint.analytic_confidence_routes_v30_4.confidence_assessments", lambda claim_id: [])
    monkeypatch.setattr(
        "src.socmint.analytic_confidence_routes_v30_4.assess_confidence",
        lambda **kwargs: {
            "status": "analytic_confidence_assessed",
            "claim_id": kwargs["claim_id"],
            "confidence_assessment_id": "confidence-1",
        },
    )
    register_analytic_confidence_routes_v30_4(app)
    client = app.test_client()

    path = "/api/v1/analytic-review/claims/claim-1/confidence-assessments"
    assert client.get(path).status_code == 401

    with client.session_transaction() as session:
        session["user"] = "viewer"
    assert client.get(path).status_code == 403

    with client.session_transaction() as session:
        session["user"] = "admin"
    response = client.post(path, json={"confirmed": True})
    assert response.status_code == 200
    assert response.get_json()["confidence_assessment_id"] == "confidence-1"
