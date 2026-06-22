from flask import Flask

from src.socmint.draft_dossier_revision_routes_v31_2 import (
    register_draft_dossier_revision_routes_v31_2,
)


def test_v31_2_draft_revision_routes_require_admin_and_create(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "test-secret"
    monkeypatch.setattr(
        "src.socmint.draft_dossier_revision_routes_v31_2.actor_is_administrator",
        lambda actor: actor == "admin",
    )
    monkeypatch.setattr(
        "src.socmint.draft_dossier_revision_routes_v31_2.current_draft_revisions",
        lambda: [],
    )
    monkeypatch.setattr(
        "src.socmint.draft_dossier_revision_routes_v31_2.assemble_draft_dossier_revision",
        lambda **kwargs: {
            "status": "draft_dossier_revision_assembled",
            "draft_revision_id": "draft-dossier-revision-1",
        },
    )
    register_draft_dossier_revision_routes_v31_2(app)
    client = app.test_client()

    assert client.get("/api/v1/publication-review/draft-revisions").status_code == 401

    with client.session_transaction() as session:
        session["user"] = "viewer"
    assert client.get("/api/v1/publication-review/draft-revisions").status_code == 403

    with client.session_transaction() as session:
        session["user"] = "admin"
    response = client.post(
        "/api/v1/publication-review/candidates/publication-candidate-1/draft-revisions",
        json={
            "revision_label": "Draft 1",
            "editorial_note": "Initial assembly",
            "reason": "operator request",
            "confirmed": True,
        },
    )
    assert response.status_code == 201
    assert response.get_json()["draft_revision_id"] == "draft-dossier-revision-1"
