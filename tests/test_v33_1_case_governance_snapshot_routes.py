from flask import Flask

from src.socmint.case_governance_snapshot_routes_v33_1 import (
    register_case_governance_snapshot_routes_v33_1,
)


def test_v33_1_snapshot_route_requires_admin_and_returns_read_model(
    monkeypatch,
):
    app = Flask(__name__)
    app.secret_key = "test-secret"
    monkeypatch.setattr(
        "src.socmint.case_governance_snapshot_routes_v33_1."
        "actor_is_administrator",
        lambda actor: actor == "admin",
    )
    monkeypatch.setattr(
        "src.socmint.case_governance_snapshot_routes_v33_1."
        "build_case_governance_snapshot",
        lambda case_id: {
            "schema": "socmint.case_governance_snapshot.v33_1",
            "version": "v33.1.0",
            "status": "ready",
            "case_id": case_id,
            "read_only": True,
        },
    )
    register_case_governance_snapshot_routes_v33_1(app)
    client = app.test_client()

    response = client.get(
        "/api/v1/dissemination-governance/cases/case-1/"
        "governance-snapshot"
    )
    assert response.status_code == 401

    with client.session_transaction() as current_session:
        current_session["user"] = "viewer"
    response = client.get(
        "/api/v1/dissemination-governance/cases/case-1/"
        "governance-snapshot"
    )
    assert response.status_code == 403

    with client.session_transaction() as current_session:
        current_session["user"] = "admin"
    response = client.get(
        "/api/v1/dissemination-governance/cases/case-1/"
        "governance-snapshot"
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["case_id"] == "case-1"
    assert payload["read_only"] is True
