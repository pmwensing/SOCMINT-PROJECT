from flask import Flask

from src.socmint.corroboration_claim_routes_v30_1 import (
    register_corroboration_claim_routes_v30_1,
)


def test_v30_1_claim_routes_require_admin_and_create(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "test-secret"
    monkeypatch.setattr(
        "src.socmint.corroboration_claim_routes_v30_1.actor_is_administrator",
        lambda actor: actor == "admin",
    )
    monkeypatch.setattr(
        "src.socmint.corroboration_claim_routes_v30_1.current_claims", lambda: []
    )
    monkeypatch.setattr(
        "src.socmint.corroboration_claim_routes_v30_1.create_corroboration_claim",
        lambda **kwargs: {
            "status": "corroboration_claim_created",
            "claim_id": "claim-1",
        },
    )
    register_corroboration_claim_routes_v30_1(app)
    client = app.test_client()

    assert client.get("/api/v1/analytic-review/claims").status_code == 401
    with client.session_transaction() as session:
        session["user"] = "viewer"
    assert client.get("/api/v1/analytic-review/claims").status_code == 403

    with client.session_transaction() as session:
        session["user"] = "admin"
    response = client.post("/api/v1/analytic-review/claims", json={"confirmed": True})
    assert response.status_code == 200
    assert response.get_json()["claim_id"] == "claim-1"
