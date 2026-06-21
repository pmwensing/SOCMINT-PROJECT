from flask import Flask

from src.socmint.immutable_published_revision_routes_v31_5 import (
    register_immutable_published_revision_routes_v31_5,
)


def test_v31_5_routes_require_admin_and_create(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "test-secret"
    monkeypatch.setattr(
        "src.socmint.immutable_published_revision_routes_v31_5.actor_is_administrator",
        lambda actor: actor == "admin",
    )
    monkeypatch.setattr(
        "src.socmint.immutable_published_revision_routes_v31_5.current_published_revisions",
        lambda: [],
    )
    monkeypatch.setattr(
        "src.socmint.immutable_published_revision_routes_v31_5.create_immutable_published_revision",
        lambda **kwargs: {
            "status": "published_revision_created",
            "published_revision_id": "published-dossier-revision-1",
        },
    )
    register_immutable_published_revision_routes_v31_5(app)
    client = app.test_client()

    assert client.get("/api/v1/publication-review/published-revisions").status_code == 401

    with client.session_transaction() as session:
        session["user"] = "viewer"
    assert client.get("/api/v1/publication-review/published-revisions").status_code == 403

    with client.session_transaction() as session:
        session["user"] = "admin"
    response = client.post(
        "/api/v1/publication-review/draft-revisions/draft-dossier-revision-1/published-revisions",
        json={
            "publication_label": "Release 1",
            "publication_note": "Approved release",
            "reason": "operator request",
            "confirmed": True,
        },
    )
    assert response.status_code == 201
    assert response.get_json()["published_revision_id"] == "published-dossier-revision-1"
