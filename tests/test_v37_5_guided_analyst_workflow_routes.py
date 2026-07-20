from pathlib import Path

from flask import Flask

from src.socmint import guided_analyst_workflow_routes_v37_5 as routes


def _app(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "v37-5-route-secret"
    routes.register_guided_analyst_workflow_routes_v37_5(app)
    monkeypatch.setattr(routes, "actor_is_administrator", lambda actor: actor == "admin")
    monkeypatch.setattr(
        routes,
        "build_guided_analyst_workflow",
        lambda: {
            "schema": "socmint.guided_analyst_workflow.v37_5",
            "read_only": True,
            "controls": {"write_actions_exposed_by_workflow": []},
        },
    )
    return app


def _login(client, user):
    with client.session_transaction() as state:
        state["user"] = user


def test_v37_5_route_requires_administrator(monkeypatch):
    client = _app(monkeypatch).test_client()
    path = "/api/v1/operational-case-intelligence/workflow"
    assert client.get(path).status_code == 401
    _login(client, "viewer")
    assert client.get(path).status_code == 403
    _login(client, "admin")
    response = client.get(path)
    assert response.status_code == 200
    assert response.get_json()["read_only"] is True
    assert response.get_json()["controls"]["write_actions_exposed_by_workflow"] == []


def test_v37_5_registration_is_read_only():
    root = Path(__file__).resolve().parents[1]
    chain = (root / "src/socmint/analytic_review_routes_v30_0.py").read_text(
        encoding="utf-8"
    )
    route_source = (
        root / "src/socmint/guided_analyst_workflow_routes_v37_5.py"
    ).read_text(encoding="utf-8")
    assert "register_guided_analyst_workflow_routes_v37_5" in chain
    assert "register_guided_analyst_workflow_routes_v37_5(app)" in chain
    assert "@app.post" not in route_source
    assert "@app.put" not in route_source
    assert "@app.delete" not in route_source
