from __future__ import annotations

from pathlib import Path

from flask import Flask

from src.socmint import canonical_observation_routes_v36_2 as routes


def _app(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "v36-2-route-secret"
    routes.register_canonical_observation_routes_v36_2(app)
    monkeypatch.setattr(
        routes,
        "actor_is_administrator",
        lambda actor: actor == "admin",
    )
    monkeypatch.setattr(
        routes,
        "current_observations",
        lambda: [
            {
                "canonical_observation_id": "canonical-observation-1",
                "observation_state": "accepted",
                "truth_assigned": False,
            }
        ],
    )
    monkeypatch.setattr(
        routes,
        "find_canonical_observation",
        lambda observation_id: (
            {
                "canonical_observation_id": observation_id,
                "observation_state": "accepted",
                "truth_assigned": False,
            }
            if observation_id == "canonical-observation-1"
            else None
        ),
    )
    monkeypatch.setattr(
        routes,
        "register_canonical_observation",
        lambda **kwargs: {
            "status": "canonical_observation_registered",
            "canonical_observation_id": "canonical-observation-1",
            "truth_assigned": False,
            "actor": kwargs["actor"],
        },
    )
    monkeypatch.setattr(
        routes,
        "change_canonical_observation_state",
        lambda **kwargs: {
            "status": "canonical_observation_state_changed",
            "canonical_observation_id": kwargs["canonical_observation_id"],
            "to_state": kwargs["to_state"],
            "truth_assigned": False,
        },
    )
    return app


def _login(client, user):
    with client.session_transaction() as state:
        state["user"] = user


def test_v36_2_routes_require_administrator(monkeypatch):
    client = _app(monkeypatch).test_client()
    assert client.get("/api/v1/entity-accuracy/observations").status_code == 401
    _login(client, "viewer")
    assert client.get("/api/v1/entity-accuracy/observations").status_code == 403
    _login(client, "admin")
    response = client.get("/api/v1/entity-accuracy/observations")
    assert response.status_code == 200
    assert response.get_json()["count"] == 1
    assert response.get_json()["truth_assigned"] is False


def test_v36_2_create_detail_and_state_routes(monkeypatch):
    client = _app(monkeypatch).test_client()
    _login(client, "admin")
    created = client.post(
        "/api/v1/entity-accuracy/observations",
        json={
            "case_id": "case-a",
            "source_id": "source-record-1",
            "source_observation_id": "evidence-observation-1",
            "tool_run_id": "collection-job-1",
            "artifact_id": "evidence-artifact-1",
            "observation_type": "email_address",
            "raw_value": "User@Example.Test",
            "normalized_value": "user@example.test",
            "observed_at": "2026-07-20T03:00:00+00:00",
            "extraction_method": "json_path",
            "extraction_confidence": 0.9,
            "context": {"field": "contact.email"},
            "adapter_format": "json",
            "adapter_name": "adapter",
            "adapter_version": "1.0.0",
            "quarantine_reasons": [],
            "reason": "Normalize.",
            "confirmed": True,
        },
    )
    assert created.status_code == 200
    assert created.get_json()["actor"] == "admin"

    detail = client.get(
        "/api/v1/entity-accuracy/observations/canonical-observation-1"
    )
    assert detail.status_code == 200
    assert detail.get_json()["observation_state"] == "accepted"
    assert client.get(
        "/api/v1/entity-accuracy/observations/missing"
    ).status_code == 404

    changed = client.post(
        "/api/v1/entity-accuracy/observations/canonical-observation-1/state",
        json={
            "to_state": "rejected",
            "reason": "Reviewed.",
            "confirmed": True,
        },
    )
    assert changed.status_code == 200
    assert changed.get_json()["to_state"] == "rejected"


def test_v36_2_state_filter_and_registration_chain(monkeypatch):
    client = _app(monkeypatch).test_client()
    _login(client, "admin")
    response = client.get(
        "/api/v1/entity-accuracy/observations?state=accepted"
    )
    assert response.status_code == 200
    assert response.get_json()["count"] == 1

    root = Path(__file__).resolve().parents[1]
    source = (root / "src/socmint/analytic_review_routes_v30_0.py").read_text(
        encoding="utf-8"
    )
    assert "register_canonical_observation_routes_v36_2" in source
    assert "register_canonical_observation_routes_v36_2(app)" in source
