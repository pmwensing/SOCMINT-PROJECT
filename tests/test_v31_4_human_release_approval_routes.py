from flask import Flask

from src.socmint.human_release_approval_routes_v31_4 import (
    register_human_release_approval_routes_v31_4,
)


def test_v31_4_release_approval_routes_require_admin_and_create(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "test-secret"
    monkeypatch.setattr(
        "src.socmint.human_release_approval_routes_v31_4.actor_is_administrator",
        lambda actor: actor == "admin",
    )
    monkeypatch.setattr(
        "src.socmint.human_release_approval_routes_v31_4.current_release_approvals",
        lambda: [],
    )
    monkeypatch.setattr(
        "src.socmint.human_release_approval_routes_v31_4.record_human_release_decision",
        lambda **kwargs: {
            "status": "approved",
            "release_approval_id": "human-release-approval-1",
        },
    )
    register_human_release_approval_routes_v31_4(app)
    client = app.test_client()

    assert client.get("/api/v1/publication-review/release-approvals").status_code == 401

    with client.session_transaction() as session:
        session["user"] = "viewer"
    assert client.get("/api/v1/publication-review/release-approvals").status_code == 403

    with client.session_transaction() as session:
        session["user"] = "admin"
    response = client.post(
        "/api/v1/publication-review/draft-revisions/draft-dossier-revision-1/release-approvals",
        json={
            "decision": "approve",
            "note": "Human review complete",
            "reason": "operator request",
            "confirmed": True,
        },
    )
    assert response.status_code == 201
    assert response.get_json()["status"] == "approved"
