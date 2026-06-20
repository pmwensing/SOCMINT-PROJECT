from flask import Flask

from src.socmint.claim_source_linkage_routes_v30_2 import register_claim_source_linkage_routes_v30_2


def test_v30_2_linkage_routes_require_admin_and_link(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "test-secret"
    monkeypatch.setattr("src.socmint.claim_source_linkage_routes_v30_2.actor_is_administrator", lambda actor: actor == "admin")
    monkeypatch.setattr("src.socmint.claim_source_linkage_routes_v30_2.claim_linkages", lambda claim_id: [])
    monkeypatch.setattr(
        "src.socmint.claim_source_linkage_routes_v30_2.link_claim_sources",
        lambda **kwargs: {
            "status": "corroboration_claim_sources_linked",
            "claim_id": kwargs["claim_id"],
            "linkage_id": "linkage-1",
        },
    )
    register_claim_source_linkage_routes_v30_2(app)
    client = app.test_client()

    assert client.get("/api/v1/analytic-review/claims/claim-1/source-linkages").status_code == 401

    with client.session_transaction() as session:
        session["user"] = "viewer"
    assert client.get("/api/v1/analytic-review/claims/claim-1/source-linkages").status_code == 403

    with client.session_transaction() as session:
        session["user"] = "admin"
    response = client.post(
        "/api/v1/analytic-review/claims/claim-1/source-linkages",
        json={"artifact_ids": ["artifact-1"], "confirmed": True},
    )
    assert response.status_code == 200
    assert response.get_json()["linkage_id"] == "linkage-1"
