from __future__ import annotations

from pathlib import Path

from flask import Flask

from src.socmint import entity_candidate_resolution_routes_v36_3 as routes


def _app(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "v36-3-route-secret"
    routes.register_entity_candidate_resolution_routes_v36_3(app)
    monkeypatch.setattr(
        routes,
        "actor_is_administrator",
        lambda actor: actor == "admin",
    )
    monkeypatch.setattr(
        routes,
        "current_candidates",
        lambda: [
            {
                "candidate_id": "entity-candidate-1",
                "scoring": {"recommendation": "possible_same_entity"},
                "identity_merged": False,
            }
        ],
    )
    monkeypatch.setattr(
        routes,
        "find_candidate",
        lambda candidate_id: (
            {"candidate_id": candidate_id, "identity_merged": False}
            if candidate_id == "entity-candidate-1"
            else None
        ),
    )
    monkeypatch.setattr(
        routes,
        "assess_entity_candidate",
        lambda **kwargs: {
            "status": "entity_candidate_assessed",
            "candidate_id": "entity-candidate-1",
            "actor": kwargs["actor"],
            "identity_merged": False,
        },
    )
    monkeypatch.setattr(
        routes,
        "record_entity_candidate_decision",
        lambda **kwargs: {
            "status": "entity_candidate_decision_recorded",
            "candidate_id": kwargs["candidate_id"],
            "decision": kwargs["decision"],
            "identity_merged": False,
        },
    )
    return app


def _login(client, user):
    with client.session_transaction() as state:
        state["user"] = user


def test_v36_3_routes_require_administrator(monkeypatch):
    client = _app(monkeypatch).test_client()
    path = "/api/v1/entity-accuracy/entity-candidates"
    assert client.get(path).status_code == 401
    _login(client, "viewer")
    assert client.get(path).status_code == 403
    _login(client, "admin")
    response = client.get(path)
    assert response.status_code == 200
    assert response.get_json()["automatic_merge_allowed"] is False


def test_v36_3_create_detail_and_decision_routes(monkeypatch):
    client = _app(monkeypatch).test_client()
    _login(client, "admin")
    created = client.post(
        "/api/v1/entity-accuracy/entity-candidates",
        json={
            "case_id": "case-a",
            "entity_a_id": "entity-a",
            "entity_b_id": "entity-b",
            "signals": [
                {
                    "signal_type": "exact_unique_identifier",
                    "observation_ids": ["obs-1"],
                    "reason": "Exact identifier.",
                }
            ],
            "limitations": [],
            "reason": "Assess.",
            "confirmed": True,
        },
    )
    assert created.status_code == 200
    assert created.get_json()["actor"] == "admin"
    assert created.get_json()["identity_merged"] is False

    detail = client.get(
        "/api/v1/entity-accuracy/entity-candidates/entity-candidate-1"
    )
    assert detail.status_code == 200
    assert client.get(
        "/api/v1/entity-accuracy/entity-candidates/missing"
    ).status_code == 404

    decision = client.post(
        "/api/v1/entity-accuracy/entity-candidates/"
        "entity-candidate-1/decision",
        json={
            "decision": "keep_separate",
            "rationale": "Conflicting control evidence.",
            "confirmed": True,
        },
    )
    assert decision.status_code == 200
    assert decision.get_json()["decision"] == "keep_separate"
    assert decision.get_json()["identity_merged"] is False


def test_v36_3_registration_chain_and_no_merge_route():
    root = Path(__file__).resolve().parents[1]
    chain = (root / "src/socmint/analytic_review_routes_v30_0.py").read_text(
        encoding="utf-8"
    )
    route_source = (
        root / "src/socmint/entity_candidate_resolution_routes_v36_3.py"
    ).read_text(encoding="utf-8")
    service_source = (
        root / "src/socmint/entity_candidate_resolution_v36_3.py"
    ).read_text(encoding="utf-8")
    assert "register_entity_candidate_resolution_routes_v36_3(app)" in chain
    assert "/merge" not in route_source
    assert "apply_merge_candidate" not in service_source
    assert "upsert_identity" not in service_source
