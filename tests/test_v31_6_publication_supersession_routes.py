from flask import Flask

from src.socmint.publication_supersession_routes_v31_6 import (
    register_publication_supersession_routes_v31_6,
)


def test_v31_6_routes_require_admin_and_create(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "test-secret"
    monkeypatch.setattr(
        "src.socmint.publication_supersession_routes_v31_6.actor_is_administrator",
        lambda actor: actor == "admin",
    )
    monkeypatch.setattr(
        "src.socmint.publication_supersession_routes_v31_6.supersession_history",
        lambda: [],
    )
    monkeypatch.setattr(
        "src.socmint.publication_supersession_routes_v31_6.record_publication_supersession",
        lambda **kwargs: {
            "status": "supersession_recorded",
            "supersession_id": "published-revision-supersession-1",
        },
    )
    register_publication_supersession_routes_v31_6(app)
    client = app.test_client()

    assert client.get("/api/v1/publication-review/supersessions").status_code == 401

    with client.session_transaction() as session:
        session["user"] = "viewer"
    assert client.get("/api/v1/publication-review/supersessions").status_code == 403

    with client.session_transaction() as session:
        session["user"] = "admin"
    response = client.post(
        "/api/v1/publication-review/supersessions",
        json={
            "predecessor_revision_id": "published-dossier-revision-1",
            "successor_revision_id": "published-dossier-revision-2",
            "reason": "corrected publication",
            "note": "new version",
            "confirmed": True,
        },
    )
    assert response.status_code == 201
    assert response.get_json()["status"] == "supersession_recorded"
