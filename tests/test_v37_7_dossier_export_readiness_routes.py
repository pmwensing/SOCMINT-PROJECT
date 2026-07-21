from pathlib import Path

from flask import Flask

from src.socmint import dossier_export_readiness_routes_v37_7 as routes


def _app(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "v37-7-route-secret"
    routes.register_dossier_export_readiness_routes_v37_7(app)
    monkeypatch.setattr(routes, "actor_is_administrator", lambda actor: actor == "admin")
    monkeypatch.setattr(
        routes,
        "current_export_readiness_records",
        lambda: [{"dossier_export_readiness_id": "readiness-1"}],
    )
    monkeypatch.setattr(
        routes,
        "find_export_readiness",
        lambda readiness_id: (
            {"dossier_export_readiness_id": readiness_id}
            if readiness_id == "readiness-1"
            else None
        ),
    )
    monkeypatch.setattr(
        routes,
        "assess_dossier_export_readiness",
        lambda **kwargs: {
            "status": "dossier_export_readiness_recorded",
            "readiness_status": "ready",
            "export_created": False,
            "published": False,
        },
    )
    return app


def _login(client, user):
    with client.session_transaction() as state:
        state["user"] = user


def test_v37_7_routes_require_administrator(monkeypatch):
    client = _app(monkeypatch).test_client()
    path = "/api/v1/dossier-export-readiness"
    assert client.get(path).status_code == 401
    _login(client, "viewer")
    assert client.get(path).status_code == 403
    _login(client, "admin")
    payload = client.get(path).get_json()
    assert payload["count"] == 1
    assert payload["export_created"] is False
    assert payload["published"] is False


def test_v37_7_assessment_and_detail_routes(monkeypatch):
    client = _app(monkeypatch).test_client()
    _login(client, "admin")
    response = client.post(
        "/api/v1/dossier-export-readiness",
        json={
            "snapshot_id": "snapshot-1",
            "redaction_review_id": "redaction-1",
            "scope_review_id": "scope-1",
            "quality_gate_reference": "quality-1",
            "approval_reference": "approval-1",
            "manifest_reference": "manifest-1",
            "chronology_reviewed": True,
            "unresolved_exceptions": [],
            "reason": "Assess.",
            "confirmed": True,
        },
    )
    assert response.status_code == 200
    assert response.get_json()["readiness_status"] == "ready"
    assert response.get_json()["export_created"] is False
    assert client.get(
        "/api/v1/dossier-export-readiness/readiness-1"
    ).status_code == 200
    assert client.get(
        "/api/v1/dossier-export-readiness/missing"
    ).status_code == 404


def test_v37_7_has_no_export_or_publish_route():
    root = Path(__file__).resolve().parents[1]
    chain = (root / "src/socmint/analytic_review_routes_v30_0.py").read_text(
        encoding="utf-8"
    )
    route_source = (
        root / "src/socmint/dossier_export_readiness_routes_v37_7.py"
    ).read_text(encoding="utf-8")
    service_source = (
        root / "src/socmint/dossier_export_readiness_v37_7.py"
    ).read_text(encoding="utf-8")
    assert "register_dossier_export_readiness_routes_v37_7" in chain
    assert "register_dossier_export_readiness_routes_v37_7(app)" in chain
    assert "/export" not in route_source
    assert "/publish" not in route_source
    assert "export_created" in service_source
    assert "existing_export_services_remain_authoritative" in service_source
