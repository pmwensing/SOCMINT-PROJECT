from flask import Flask

from src.socmint.editorial_validation_routes_v31_3 import (
    register_editorial_validation_routes_v31_3,
)


def test_v31_3_editorial_routes_require_admin_and_create(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "test-secret"
    monkeypatch.setattr(
        "src.socmint.editorial_validation_routes_v31_3.actor_is_administrator",
        lambda actor: actor == "admin",
    )
    monkeypatch.setattr(
        "src.socmint.editorial_validation_routes_v31_3.current_editorial_validations",
        lambda: [],
    )
    monkeypatch.setattr(
        "src.socmint.editorial_validation_routes_v31_3.run_editorial_validation",
        lambda **kwargs: {
            "status": "editorial_validation_recorded",
            "editorial_validation_id": "editorial-validation-1",
            "gate_status": "passed",
        },
    )
    register_editorial_validation_routes_v31_3(app)
    client = app.test_client()

    assert client.get("/api/v1/publication-review/editorial-validations").status_code == 401

    with client.session_transaction() as session:
        session["user"] = "viewer"
    assert client.get("/api/v1/publication-review/editorial-validations").status_code == 403

    with client.session_transaction() as session:
        session["user"] = "admin"
    response = client.post(
        "/api/v1/publication-review/draft-revisions/draft-dossier-revision-1/editorial-validations",
        json={
            "editorial_summary": "Review complete",
            "policy_acknowledgements": {
                "provenance_reviewed": True,
                "privacy_reviewed": True,
                "legal_basis_confirmed": True,
                "audience_scope_confirmed": True,
            },
            "reason": "operator request",
            "confirmed": True,
        },
    )
    assert response.status_code == 201
    assert response.get_json()["gate_status"] == "passed"
