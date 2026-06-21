from flask import Flask

from src.socmint.publication_candidate_routes_v31_1 import (
    register_publication_candidate_routes_v31_1,
)


def test_v31_1_candidate_routes_require_admin_and_create(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "test-secret"
    monkeypatch.setattr(
        "src.socmint.publication_candidate_routes_v31_1.actor_is_administrator",
        lambda actor: actor == "admin",
    )
    monkeypatch.setattr(
        "src.socmint.publication_candidate_routes_v31_1.current_publication_candidates",
        lambda: [],
    )
    monkeypatch.setattr(
        "src.socmint.publication_candidate_routes_v31_1.create_publication_candidate",
        lambda **kwargs: {
            "status": "publication_candidate_recorded",
            "publication_candidate_id": "publication-candidate-1",
        },
    )
    register_publication_candidate_routes_v31_1(app)
    client = app.test_client()

    assert client.get("/api/v1/publication-review/candidates").status_code == 401

    with client.session_transaction() as session:
        session["user"] = "viewer"
    assert client.get("/api/v1/publication-review/candidates").status_code == 403

    with client.session_transaction() as session:
        session["user"] = "admin"
    response = client.post(
        "/api/v1/publication-review/candidates",
        json={
            "dossier_contribution_id": "dossier-contribution-approved",
            "publication_purpose": "release",
            "release_scope": "internal",
            "rationale": "ready",
            "reason": "operator request",
            "confirmed": True,
        },
    )
    assert response.status_code == 201
    assert response.get_json()["publication_candidate_id"] == "publication-candidate-1"
