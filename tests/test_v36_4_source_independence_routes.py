from __future__ import annotations

from pathlib import Path

from flask import Flask

from src.socmint import source_independence_routes_v36_4 as routes


def _app(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "v36-4-route-secret"
    routes.register_source_independence_routes_v36_4(app)
    monkeypatch.setattr(
        routes,
        "actor_is_administrator",
        lambda actor: actor == "admin",
    )
    monkeypatch.setattr(
        routes,
        "current_independence_assessments",
        lambda: [
            {
                "independence_group_id": "source-independence-group-1",
                "relationship": "independent",
                "source_mutated": False,
            }
        ],
    )
    monkeypatch.setattr(
        routes,
        "find_independence_group",
        lambda group_id: (
            {"independence_group_id": group_id, "source_mutated": False}
            if group_id == "source-independence-group-1"
            else None
        ),
    )
    monkeypatch.setattr(
        routes,
        "assess_source_independence",
        lambda **kwargs: {
            "status": "source_independence_assessed",
            "independence_group_id": "source-independence-group-1",
            "relationship": kwargs["relationship"],
            "source_mutated": False,
        },
    )
    return app


def _login(client, user):
    with client.session_transaction() as state:
        state["user"] = user


def test_v36_4_routes_require_administrator(monkeypatch):
    client = _app(monkeypatch).test_client()
    path = "/api/v1/entity-accuracy/source-independence"
    assert client.get(path).status_code == 401
    _login(client, "viewer")
    assert client.get(path).status_code == 403
    _login(client, "admin")
    response = client.get(path)
    assert response.status_code == 200
    assert response.get_json()["source_mutated"] is False


def test_v36_4_create_and_detail_routes(monkeypatch):
    client = _app(monkeypatch).test_client()
    _login(client, "admin")
    created = client.post(
        "/api/v1/entity-accuracy/source-independence",
        json={
            "case_id": "case-a",
            "source_ids": ["source-a", "source-b"],
            "relationship": "independent",
            "signals": [
                {
                    "signal_type": "independent_primary_capture",
                    "reason": "Separate origins.",
                }
            ],
            "limitations": [],
            "reason": "Assess.",
            "confirmed": True,
        },
    )
    assert created.status_code == 200
    assert created.get_json()["relationship"] == "independent"
    assert created.get_json()["source_mutated"] is False

    detail = client.get(
        "/api/v1/entity-accuracy/source-independence/"
        "source-independence-group-1"
    )
    assert detail.status_code == 200
    assert client.get(
        "/api/v1/entity-accuracy/source-independence/missing"
    ).status_code == 404


def test_v36_4_registration_chain_and_no_source_update_route():
    root = Path(__file__).resolve().parents[1]
    chain = (root / "src/socmint/analytic_review_routes_v30_0.py").read_text(
        encoding="utf-8"
    )
    routes_source = (
        root / "src/socmint/source_independence_routes_v36_4.py"
    ).read_text(encoding="utf-8")
    assert "register_source_independence_routes_v36_4(app)" in chain
    assert "@app.put" not in routes_source
    assert "@app.patch" not in routes_source
    assert "update_source" not in routes_source
