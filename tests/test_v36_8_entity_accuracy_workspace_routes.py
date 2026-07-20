from __future__ import annotations

from pathlib import Path

from flask import Flask

from src.socmint import entity_accuracy_workspace_routes_v36_8 as routes


def _app(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    app = Flask(
        __name__,
        template_folder=str(root / "src/socmint/templates"),
    )
    app.secret_key = "v36-8-route-secret"
    app.add_url_rule(
        "/",
        endpoint="dashboard.index",
        view_func=lambda: "index",
    )
    app.add_url_rule(
        "/login",
        endpoint="dashboard.login",
        view_func=lambda: "login",
    )
    app.add_url_rule(
        "/logout",
        endpoint="dashboard.logout",
        view_func=lambda: "logout",
    )
    routes.register_entity_accuracy_workspace_routes_v36_8(app)
    monkeypatch.setattr(
        routes,
        "actor_is_administrator",
        lambda actor: actor == "admin",
    )
    monkeypatch.setattr(
        routes,
        "build_entity_accuracy_workspace",
        lambda: {
            "status": "ready",
            "read_only": True,
            "summary": {
                "source_count": 2,
                "canonical_observation_count": 3,
                "entity_candidate_count": 1,
                "source_independence_group_count": 1,
                "claim_verification_count": 2,
                "relationship_timeline_count": 1,
                "dossier_snapshot_count": 1,
                "finding_count": 1,
            },
            "findings": [
                {
                    "key": "alternative_ranking_tied",
                    "severity": "attention",
                    "count": 1,
                    "message": "Alternative claims are tied.",
                    "next_action": "Retain the tie.",
                }
            ],
            "source_inventory": [],
            "observation_inventory": [],
            "entity_candidate_inventory": [],
            "source_independence_inventory": [],
            "claim_verification_inventory": [],
            "relationship_timeline_inventory": [],
            "dossier_snapshot_inventory": [],
            "controls": {"write_actions_exposed_by_workspace": []},
        },
    )
    return app


def _login(client, user):
    with client.session_transaction() as state:
        state["user"] = user


def test_v36_8_workspace_requires_administrator(monkeypatch):
    client = _app(monkeypatch).test_client()
    response = client.get("/entity-accuracy")
    assert response.status_code == 302
    _login(client, "viewer")
    assert client.get("/entity-accuracy").status_code == 403
    assert client.get("/api/v1/entity-accuracy/workspace").status_code == 403
    _login(client, "admin")
    assert client.get("/entity-accuracy").status_code == 200
    assert client.get("/api/v1/entity-accuracy/workspace").status_code == 200


def test_v36_8_template_is_explicitly_read_only(monkeypatch):
    client = _app(monkeypatch).test_client()
    _login(client, "admin")
    body = client.get("/entity-accuracy").get_data(as_text=True)
    assert 'data-entity-accuracy-workspace="v36.8"' in body
    assert 'data-read-only="true"' in body
    assert 'data-automatic-truth-assignment="false"' in body
    assert 'data-automatic-entity-merge="false"' in body
    assert 'data-automatic-dossier-publication="false"' in body
    assert 'data-write-actions="none"' in body
    assert 'data-finding-key="alternative_ranking_tied"' in body
    assert "no merge, approval, export, publication" in body.lower()
    assert "<form" not in body.lower()
    assert "<button" not in body.lower()


def test_v36_8_api_exposes_complete_summary_without_write_controls(monkeypatch):
    client = _app(monkeypatch).test_client()
    _login(client, "admin")
    payload = client.get("/api/v1/entity-accuracy/workspace").get_json()
    assert payload["read_only"] is True
    assert payload["summary"]["source_count"] == 2
    assert payload["summary"]["dossier_snapshot_count"] == 1
    assert payload["controls"]["write_actions_exposed_by_workspace"] == []


def test_v36_8_is_registered_through_analytic_review_chain():
    root = Path(__file__).resolve().parents[1]
    chain = (root / "src/socmint/analytic_review_routes_v30_0.py").read_text(
        encoding="utf-8"
    )
    assert "register_entity_accuracy_workspace_routes_v36_8" in chain
    assert "register_entity_accuracy_workspace_routes_v36_8(app)" in chain
