from __future__ import annotations

from pathlib import Path

from flask import Flask

from src.socmint import dossier_synthesis_routes_v36_7 as routes


def _app(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "v36-7-route-secret"
    routes.register_dossier_synthesis_routes_v36_7(app)
    monkeypatch.setattr(
        routes,
        "actor_is_administrator",
        lambda actor: actor == "admin",
    )
    monkeypatch.setattr(
        routes,
        "current_snapshots",
        lambda: [
            {
                "dossier_synthesis_snapshot_id": "snapshot-1",
                "export_created": False,
                "published": False,
            }
        ],
    )
    monkeypatch.setattr(
        routes,
        "find_snapshot",
        lambda snapshot_id: (
            {"dossier_synthesis_snapshot_id": snapshot_id}
            if snapshot_id == "snapshot-1"
            else None
        ),
    )
    monkeypatch.setattr(
        routes,
        "latest_snapshot",
        lambda case_id, entity_id: {
            "case_id": case_id,
            "entity_id": entity_id,
            "snapshot_version": 2,
        },
    )
    monkeypatch.setattr(
        routes,
        "create_dossier_synthesis_snapshot",
        lambda **kwargs: {
            "status": "dossier_synthesis_snapshot_created",
            "dossier_synthesis_snapshot_id": "snapshot-1",
            "export_created": False,
            "published": False,
        },
    )
    return app


def _login(client, user):
    with client.session_transaction() as state:
        state["user"] = user


def test_v36_7_routes_require_administrator(monkeypatch):
    client = _app(monkeypatch).test_client()
    path = "/api/v1/entity-accuracy/dossier-snapshots"
    assert client.get(path).status_code == 401
    _login(client, "viewer")
    assert client.get(path).status_code == 403
    _login(client, "admin")
    response = client.get(path)
    assert response.status_code == 200
    assert response.get_json()["export_created"] is False
    assert response.get_json()["published"] is False


def test_v36_7_create_detail_and_latest_routes(monkeypatch):
    client = _app(monkeypatch).test_client()
    _login(client, "admin")
    created = client.post(
        "/api/v1/entity-accuracy/dossier-snapshots",
        json={
            "case_id": "case-a",
            "entity_id": "entity-a",
            "display_label": "Entity A",
            "purpose": "Authorized dossier synthesis.",
            "limitations": [],
            "reason": "Create snapshot.",
            "confirmed": True,
        },
    )
    assert created.status_code == 200
    assert created.get_json()["export_created"] is False

    detail = client.get(
        "/api/v1/entity-accuracy/dossier-snapshots/snapshot-1"
    )
    assert detail.status_code == 200
    latest = client.get(
        "/api/v1/entity-accuracy/dossier-snapshots/latest"
        "?case_id=case-a&entity_id=entity-a"
    )
    assert latest.status_code == 200
    assert latest.get_json()["snapshot_version"] == 2
    assert client.get(
        "/api/v1/entity-accuracy/dossier-snapshots/latest"
    ).status_code == 400


def test_v36_7_registration_chain_has_no_export_or_publish_route():
    root = Path(__file__).resolve().parents[1]
    chain = (root / "src/socmint/analytic_review_routes_v30_0.py").read_text(
        encoding="utf-8"
    )
    route_source = (
        root / "src/socmint/dossier_synthesis_routes_v36_7.py"
    ).read_text(encoding="utf-8")
    service_source = (
        root / "src/socmint/dossier_synthesis_v36_7.py"
    ).read_text(encoding="utf-8")
    assert "register_dossier_synthesis_routes_v36_7(app)" in chain
    assert "/export" not in route_source
    assert "/publish" not in route_source
    assert "dossier_export" not in service_source
    assert "dossier_export_pack" not in service_source
