from __future__ import annotations

from pathlib import Path

from flask import Flask

from src.socmint import claim_verification_routes_v36_5 as routes


def _app(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "v36-5-route-secret"
    routes.register_claim_verification_routes_v36_5(app)
    monkeypatch.setattr(
        routes,
        "actor_is_administrator",
        lambda actor: actor == "admin",
    )
    monkeypatch.setattr(
        routes,
        "current_verifications",
        lambda: [
            {
                "claim_id": "claim-1",
                "support_score": 70,
                "truth_assigned": False,
            }
        ],
    )
    monkeypatch.setattr(
        routes,
        "find_verification",
        lambda claim_id: (
            {"claim_id": claim_id, "truth_assigned": False}
            if claim_id == "claim-1"
            else None
        ),
    )
    monkeypatch.setattr(
        routes,
        "assess_claim_verification",
        lambda **kwargs: {
            "status": "claim_verification_assessed",
            "claim_id": kwargs["claim_id"],
            "truth_assigned": False,
            "dossier_eligible": False,
        },
    )
    return app


def _login(client, user):
    with client.session_transaction() as state:
        state["user"] = user


def test_v36_5_routes_require_administrator(monkeypatch):
    client = _app(monkeypatch).test_client()
    path = "/api/v1/entity-accuracy/claim-verifications"
    assert client.get(path).status_code == 401
    _login(client, "viewer")
    assert client.get(path).status_code == 403
    _login(client, "admin")
    response = client.get(path)
    assert response.status_code == 200
    assert response.get_json()["truth_assigned"] is False


def test_v36_5_create_and_detail_routes(monkeypatch):
    client = _app(monkeypatch).test_client()
    _login(client, "admin")
    created = client.post(
        "/api/v1/entity-accuracy/claims/claim-1/verification",
        json={
            "source_ids": ["source-a", "source-b"],
            "identity_context": {
                "basis": "case_entity_bound",
                "reason": "Case entity context.",
            },
            "temporal_relevance_score": 80,
            "temporal_reason": "Current during period.",
            "limitations": [],
            "methodology": "Dimensional verification.",
            "reason": "Assess.",
            "confirmed": True,
        },
    )
    assert created.status_code == 200
    assert created.get_json()["truth_assigned"] is False
    assert created.get_json()["dossier_eligible"] is False

    detail = client.get(
        "/api/v1/entity-accuracy/claims/claim-1/verification"
    )
    assert detail.status_code == 200
    assert client.get(
        "/api/v1/entity-accuracy/claims/missing/verification"
    ).status_code == 404


def test_v36_5_registration_chain_has_no_truth_or_approval_route():
    root = Path(__file__).resolve().parents[1]
    chain = (root / "src/socmint/analytic_review_routes_v30_0.py").read_text(
        encoding="utf-8"
    )
    route_source = (
        root / "src/socmint/claim_verification_routes_v36_5.py"
    ).read_text(encoding="utf-8")
    assert "register_claim_verification_routes_v36_5(app)" in chain
    assert "/approve" not in route_source
    assert "/truth" not in route_source
    assert "/dossier" not in route_source
