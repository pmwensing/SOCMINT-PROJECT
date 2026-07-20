from pathlib import Path

from flask import Flask

from src.socmint import case_import_pilot_routes_v37_3 as routes


def _app(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "v37-3-route-secret"
    routes.register_case_import_pilot_routes_v37_3(app)
    monkeypatch.setattr(routes, "actor_is_administrator", lambda actor: actor == "admin")
    monkeypatch.setattr(
        routes,
        "current_scope_assessments",
        lambda: [{"staged_record_id": "record-1", "scope_status": "in_scope"}],
    )
    monkeypatch.setattr(
        routes,
        "current_review_decisions",
        lambda: [{"staged_record_id": "record-1", "decision": "accepted"}],
    )
    monkeypatch.setattr(
        routes,
        "find_scope_assessment",
        lambda record_id: {"staged_record_id": record_id} if record_id == "record-1" else None,
    )
    monkeypatch.setattr(
        routes,
        "find_review_decision",
        lambda record_id: {"staged_record_id": record_id} if record_id == "record-1" else None,
    )
    monkeypatch.setattr(
        routes,
        "assess_pilot_record",
        lambda **kwargs: {
            "status": "case_import_scope_assessed",
            "staged_record_id": kwargs["staged_record_id"],
            "observation_created": False,
        },
    )
    monkeypatch.setattr(
        routes,
        "record_pilot_review_decision",
        lambda **kwargs: {
            "status": "case_import_review_decision_recorded",
            "staged_record_id": kwargs["staged_record_id"],
            "observation_promotion_allowed": True,
            "observation_created": False,
        },
    )
    monkeypatch.setattr(
        routes,
        "build_evidence_location_projection",
        lambda **kwargs: {
            "status": "evidence_location_projection_ready",
            "original_uploaded_to_github": False,
        },
    )
    return app


def _login(client, user):
    with client.session_transaction() as state:
        state["user"] = user


def test_v37_3_routes_require_administrator(monkeypatch):
    client = _app(monkeypatch).test_client()
    path = "/api/v1/case-import-pilot/scope-assessments"
    assert client.get(path).status_code == 401
    _login(client, "viewer")
    assert client.get(path).status_code == 403
    _login(client, "admin")
    assert client.get(path).status_code == 200
    review = client.get("/api/v1/case-import-pilot/review-decisions").get_json()
    assert review["automatic_observation_promotion"] is False


def test_v37_3_assessment_review_and_projection_routes(monkeypatch):
    client = _app(monkeypatch).test_client()
    _login(client, "admin")
    assessed = client.post(
        "/api/v1/case-import-pilot/records/record-1/assess",
        json={"reason": "Assess.", "confirmed": True},
    )
    assert assessed.status_code == 200
    assert assessed.get_json()["observation_created"] is False
    assert client.get(
        "/api/v1/case-import-pilot/records/record-1/assessment"
    ).status_code == 200
    assert client.get(
        "/api/v1/case-import-pilot/records/missing/assessment"
    ).status_code == 404

    reviewed = client.post(
        "/api/v1/case-import-pilot/records/record-1/review",
        json={"decision": "accepted", "reason": "Review.", "confirmed": True},
    )
    assert reviewed.status_code == 200
    assert reviewed.get_json()["observation_promotion_allowed"] is True
    assert reviewed.get_json()["observation_created"] is False
    assert client.get(
        "/api/v1/case-import-pilot/records/record-1/review"
    ).status_code == 200

    location = client.post(
        "/api/v1/case-import-pilot/evidence-location-projection",
        json={
            "evidence_id": "SYNTHETIC-1",
            "location_type": "local_primary",
            "location_id": "LOCAL-1",
            "path_or_file_id": "fixture/item.json",
            "sha256": "a" * 64,
            "verified": True,
        },
    )
    assert location.status_code == 200
    assert location.get_json()["original_uploaded_to_github"] is False


def test_v37_3_is_registered_without_observation_or_export_bypass():
    root = Path(__file__).resolve().parents[1]
    chain = (root / "src/socmint/analytic_review_routes_v30_0.py").read_text(
        encoding="utf-8"
    )
    route_source = (
        root / "src/socmint/case_import_pilot_routes_v37_3.py"
    ).read_text(encoding="utf-8")
    service_source = (
        root / "src/socmint/case_import_pilot_v37_3.py"
    ).read_text(encoding="utf-8")
    assert "register_case_import_pilot_routes_v37_3" in chain
    assert "register_case_import_pilot_routes_v37_3(app)" in chain
    assert "/promote" not in route_source
    assert "/export" not in route_source
    assert "/publish" not in route_source
    assert "observation_created" in service_source
    assert "original_uploaded_to_github" in service_source
