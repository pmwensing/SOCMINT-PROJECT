from pathlib import Path

from flask import Flask

from src.socmint import relationship_chronology_workflow_routes_v37_6 as routes


def _app(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "v37-6-route-secret"
    routes.register_relationship_chronology_workflow_routes_v37_6(app)
    monkeypatch.setattr(routes, "actor_is_administrator", lambda actor: actor == "admin")
    monkeypatch.setattr(
        routes,
        "build_relationship_chronology",
        lambda **kwargs: {
            "schema": "socmint.relationship_chronology_workflow.v37_6",
            "read_only": True,
            "case_id": kwargs.get("case_id"),
            "entity_id": kwargs.get("entity_id"),
            "controls": {"write_actions_exposed": []},
        },
    )
    return app


def _login(client, user):
    with client.session_transaction() as state:
        state["user"] = user


def test_v37_6_route_requires_administrator_and_forwards_filters(monkeypatch):
    client = _app(monkeypatch).test_client()
    path = "/api/v1/operational-case-intelligence/chronology"
    assert client.get(path).status_code == 401
    _login(client, "viewer")
    assert client.get(path).status_code == 403
    _login(client, "admin")
    response = client.get(f"{path}?case_id=case-a&entity_id=entity-a")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["case_id"] == "case-a"
    assert payload["entity_id"] == "entity-a"
    assert payload["read_only"] is True
    assert payload["controls"]["write_actions_exposed"] == []


def test_v37_6_registration_is_read_only():
    root = Path(__file__).resolve().parents[1]
    chain = (root / "src/socmint/analytic_review_routes_v30_0.py").read_text(
        encoding="utf-8"
    )
    route_source = (
        root / "src/socmint/relationship_chronology_workflow_routes_v37_6.py"
    ).read_text(encoding="utf-8")
    assert "register_relationship_chronology_workflow_routes_v37_6" in chain
    assert "register_relationship_chronology_workflow_routes_v37_6(app)" in chain
    assert "@app.post" not in route_source
    assert "@app.put" not in route_source
    assert "@app.delete" not in route_source
