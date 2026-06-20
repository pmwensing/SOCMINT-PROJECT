from flask import Flask

from src.socmint.human_analytic_review_routes_v30_5 import register_human_analytic_review_routes_v30_5


def test_v30_5_routes_require_admin_and_record(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "test-secret"
    monkeypatch.setattr("src.socmint.human_analytic_review_routes_v30_5.actor_is_administrator", lambda actor: actor == "admin")
    monkeypatch.setattr("src.socmint.human_analytic_review_routes_v30_5.current_review_decisions", lambda: [])
    monkeypatch.setattr("src.socmint.human_analytic_review_routes_v30_5.reviews_for_claim", lambda claim_id: [])
    monkeypatch.setattr(
        "src.socmint.human_analytic_review_routes_v30_5.record_human_review",
        lambda **kwargs: {
            "status": "human_analytic_review_recorded",
            "claim_id": kwargs["claim_id"],
            "human_review_id": "review-1",
        },
    )
    register_human_analytic_review_routes_v30_5(app)
    client = app.test_client()

    path = "/api/v1/analytic-review/claims/claim-1/human-reviews"
    assert client.get(path).status_code == 401

    with client.session_transaction() as session:
        session["user"] = "viewer"
    assert client.get(path).status_code == 403

    with client.session_transaction() as session:
        session["user"] = "admin"
    response = client.post(path, json={"confirmed": True})
    assert response.status_code == 200
    assert response.get_json()["human_review_id"] == "review-1"
