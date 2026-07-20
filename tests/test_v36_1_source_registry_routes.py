from __future__ import annotations

from pathlib import Path

from flask import Flask

from src.socmint import source_registry_routes_v36_1 as routes


def _app(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "v36-1-route-secret"
    routes.register_source_registry_routes_v36_1(app)
    monkeypatch.setattr(
        routes,
        "actor_is_administrator",
        lambda actor: actor == "admin",
    )
    monkeypatch.setattr(
        routes,
        "current_sources",
        lambda: [{"source_id": "source-record-1", "truth_assigned": False}],
    )
    monkeypatch.setattr(
        routes,
        "find_source",
        lambda source_id: (
            {"source_id": source_id, "truth_assigned": False}
            if source_id == "source-record-1"
            else None
        ),
    )
    monkeypatch.setattr(
        routes,
        "current_reliability_profiles",
        lambda source_id: [
            {
                "source_id": source_id,
                "claim_type": "registered_ownership",
                "reliability_band": "A",
                "truth_assigned": False,
            }
        ],
    )
    monkeypatch.setattr(
        routes,
        "register_source",
        lambda **kwargs: {
            "status": "source_record_registered",
            "source_id": "source-record-1",
            "truth_assigned": False,
            "received_actor": kwargs["actor"],
        },
    )
    monkeypatch.setattr(
        routes,
        "assess_source_reliability",
        lambda **kwargs: {
            "status": "source_reliability_assessed",
            "source_id": kwargs["source_id"],
            "claim_type": kwargs["claim_type"],
            "truth_assigned": False,
        },
    )
    return app


def _login(client, user):
    with client.session_transaction() as state:
        state["user"] = user


def test_v36_1_source_routes_require_administrator(monkeypatch):
    client = _app(monkeypatch).test_client()
    assert client.get("/api/v1/entity-accuracy/sources").status_code == 401
    _login(client, "viewer")
    assert client.get("/api/v1/entity-accuracy/sources").status_code == 403
    _login(client, "admin")
    response = client.get("/api/v1/entity-accuracy/sources")
    assert response.status_code == 200
    assert response.get_json()["count"] == 1
    assert response.get_json()["truth_assigned"] is False


def test_v36_1_registers_and_reads_source_record(monkeypatch):
    client = _app(monkeypatch).test_client()
    _login(client, "admin")
    response = client.post(
        "/api/v1/entity-accuracy/sources",
        json={
            "case_id": "case-a",
            "source_type": "primary_record",
            "publisher_or_operator": "Registry",
            "canonical_url": "https://example.test/record",
            "retrieved_url": "https://example.test/record",
            "captured_at": "2026-07-20T02:00:00+00:00",
            "jurisdiction": "CA-ON",
            "access_method": "public_web",
            "authentication_required": False,
            "original_or_derived": "original",
            "terms_and_collection_notes": "Public source.",
            "content_sha256": "a" * 64,
            "capture_artifact_id": "evidence-artifact-1",
            "adapter_name": "adapter",
            "adapter_version": "1.0.0",
            "reason": "Register.",
            "confirmed": True,
        },
    )
    assert response.status_code == 200
    assert response.get_json()["status"] == "source_record_registered"
    assert response.get_json()["received_actor"] == "admin"

    detail = client.get("/api/v1/entity-accuracy/sources/source-record-1")
    assert detail.status_code == 200
    assert detail.get_json()["source_id"] == "source-record-1"
    assert client.get(
        "/api/v1/entity-accuracy/sources/missing"
    ).status_code == 404


def test_v36_1_reliability_routes_remain_claim_type_specific(monkeypatch):
    client = _app(monkeypatch).test_client()
    _login(client, "admin")
    response = client.post(
        "/api/v1/entity-accuracy/sources/source-record-1/"
        "reliability-assessments",
        json={
            "claim_type": "registered_ownership",
            "reliability_band": "A",
            "components": {
                "authority": 90,
                "directness": 90,
                "authenticity": 90,
                "capture_integrity": 100,
                "temporal_relevance": 80,
            },
            "reasons": ["Official record."],
            "limitations": [],
            "reason": "Assess.",
            "confirmed": True,
        },
    )
    assert response.status_code == 200
    assert response.get_json()["claim_type"] == "registered_ownership"
    assert response.get_json()["truth_assigned"] is False

    inventory = client.get(
        "/api/v1/entity-accuracy/sources/source-record-1/"
        "reliability-assessments"
    )
    assert inventory.status_code == 200
    assert inventory.get_json()["profiles"][0]["claim_type"] == (
        "registered_ownership"
    )
    assert client.post(
        "/api/v1/entity-accuracy/sources/source-record-1"
    ).status_code == 405


def test_v36_1_routes_are_registered_through_analytic_review_chain():
    root = Path(__file__).resolve().parents[1]
    source = (root / "src/socmint/analytic_review_routes_v30_0.py").read_text(
        encoding="utf-8"
    )
    assert "register_source_registry_routes_v36_1" in source
    assert "register_source_registry_routes_v36_1(app)" in source
