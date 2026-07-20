from __future__ import annotations

from pathlib import Path

from flask import Flask

from src.socmint import relationship_timeline_routes_v36_6 as routes


def _app(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "v36-6-route-secret"
    routes.register_relationship_timeline_routes_v36_6(app)
    monkeypatch.setattr(
        routes,
        "actor_is_administrator",
        lambda actor: actor == "admin",
    )
    monkeypatch.setattr(
        routes,
        "current_relationship_assessments",
        lambda: [
            {
                "relationship_timeline_assessment_id": "relationship-1",
                "relationship_asserted_as_truth": False,
            }
        ],
    )
    monkeypatch.setattr(
        routes,
        "timeline_for_entity",
        lambda entity_id: [{"subject_entity_id": entity_id}],
    )
    monkeypatch.setattr(
        routes,
        "find_relationship_assessment",
        lambda assessment_id: (
            {"relationship_timeline_assessment_id": assessment_id}
            if assessment_id == "relationship-1"
            else None
        ),
    )
    monkeypatch.setattr(
        routes,
        "assess_relationship_timeline",
        lambda **kwargs: {
            "status": "relationship_timeline_assessed",
            "relationship_timeline_assessment_id": "relationship-1",
            "relationship_asserted_as_truth": False,
            "graph_mutated": False,
        },
    )
    return app


def _login(client, user):
    with client.session_transaction() as state:
        state["user"] = user


def test_v36_6_routes_require_administrator(monkeypatch):
    client = _app(monkeypatch).test_client()
    path = "/api/v1/entity-accuracy/relationship-timeline"
    assert client.get(path).status_code == 401
    _login(client, "viewer")
    assert client.get(path).status_code == 403
    _login(client, "admin")
    response = client.get(path)
    assert response.status_code == 200
    assert response.get_json()["relationship_asserted_as_truth"] is False


def test_v36_6_create_detail_and_entity_filter(monkeypatch):
    client = _app(monkeypatch).test_client()
    _login(client, "admin")
    created = client.post(
        "/api/v1/entity-accuracy/relationship-timeline",
        json={
            "claim_id": "claim-1",
            "relationship_type": "person_to_organization",
            "subject_entity_id": "person-1",
            "object_entity_id": "org-1",
            "source_ids": ["source-1"],
            "observation_ids": ["observation-1"],
            "event_time": "2026-07-01T10:00:00+00:00",
            "capture_time": "2026-07-03T10:00:00+00:00",
            "inference_class": "direct_evidence",
            "inference_warning": "No causation inferred.",
            "limitations": [],
            "reason": "Assess.",
            "confirmed": True,
        },
    )
    assert created.status_code == 200
    assert created.get_json()["graph_mutated"] is False

    detail = client.get(
        "/api/v1/entity-accuracy/relationship-timeline/relationship-1"
    )
    assert detail.status_code == 200
    filtered = client.get(
        "/api/v1/entity-accuracy/relationship-timeline?entity_id=person-1"
    )
    assert filtered.status_code == 200
    assert filtered.get_json()["assessments"][0]["subject_entity_id"] == (
        "person-1"
    )


def test_v36_6_registration_chain_has_no_graph_write_route():
    root = Path(__file__).resolve().parents[1]
    chain = (root / "src/socmint/analytic_review_routes_v30_0.py").read_text(
        encoding="utf-8"
    )
    route_source = (
        root / "src/socmint/relationship_timeline_routes_v36_6.py"
    ).read_text(encoding="utf-8")
    service_source = (
        root / "src/socmint/relationship_timeline_v36_6.py"
    ).read_text(encoding="utf-8")
    assert "register_relationship_timeline_routes_v36_6(app)" in chain
    assert "upsert_identity_edge" not in service_source
    assert "/graph" not in route_source
    assert "/causation" not in route_source
