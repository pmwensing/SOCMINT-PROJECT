from pathlib import Path

from flask import Flask

from src.socmint import operational_case_intelligence_workspace_routes_v37_8 as routes


def _app(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    app = Flask(__name__, template_folder=str(root / "src/socmint/templates"))
    app.secret_key = "v37-8-route-secret"

    @app.get("/")
    def index():
        return "index"

    @app.get("/login")
    def login():
        return "login"

    @app.get("/logout")
    def logout():
        return "logout"

    app.view_functions["dashboard.index"] = app.view_functions.pop("index")
    app.view_functions["dashboard.login"] = app.view_functions.pop("login")
    app.view_functions["dashboard.logout"] = app.view_functions.pop("logout")
    routes.register_operational_case_intelligence_workspace_routes_v37_8(app)
    monkeypatch.setattr(routes, "actor_is_administrator", lambda actor: actor == "admin")
    monkeypatch.setattr(
        routes,
        "build_operational_case_intelligence_workspace",
        lambda: {
            "status": "ready",
            "read_only": True,
            "summary": {
                "import_count": 2,
                "chronology_entry_count": 1,
                "export_readiness_record_count": 1,
                "export_ready_count": 0,
            },
            "findings": [
                {
                    "key": "review_pending",
                    "message": "Review is pending.",
                    "next_action": "Complete review.",
                }
            ],
            "chronology": {
                "summary": {"entry_count": 1},
                "entries": [
                    {
                        "entry_type": "relationship_assessment",
                        "event_time": "2026-07-20T01:00:00+00:00",
                        "inference_warning": "Inference warning.",
                    }
                ],
            },
            "export_readiness_inventory": [
                {
                    "dossier_synthesis_snapshot_id": "snapshot-1",
                    "readiness_status": "not_ready",
                }
            ],
        },
    )
    return app


def _login(client, user):
    with client.session_transaction() as state:
        state["user"] = user
        state["is_admin"] = user == "admin"


def test_v37_8_workspace_requires_administrator(monkeypatch):
    client = _app(monkeypatch).test_client()
    assert client.get("/operational-case-intelligence").status_code == 302
    _login(client, "viewer")
    assert client.get("/operational-case-intelligence").status_code == 403
    assert client.get(
        "/api/v1/operational-case-intelligence/workspace"
    ).status_code == 403
    _login(client, "admin")
    assert client.get("/operational-case-intelligence").status_code == 200
    assert client.get(
        "/api/v1/operational-case-intelligence/workspace"
    ).status_code == 200


def test_v37_8_template_is_explicitly_read_only(monkeypatch):
    client = _app(monkeypatch).test_client()
    _login(client, "admin")
    body = client.get("/operational-case-intelligence").get_data(as_text=True)
    for marker in (
        'data-operational-case-intelligence-workspace="v37.8"',
        'data-read-only="true"',
        'data-automatic-collection="false"',
        'data-automatic-observation-promotion="false"',
        'data-automatic-entity-merge="false"',
        'data-automatic-claim-approval="false"',
        'data-automatic-export="false"',
        'data-automatic-publication="false"',
        'data-write-actions="none"',
        'data-import-workflow="true"',
        'data-integrity-findings="true"',
        'data-chronology="true"',
        'data-export-readiness="true"',
        'data-finding-key="review_pending"',
        'data-readiness-status="not_ready"',
    ):
        assert marker in body
    assert "<form" not in body.lower()
    assert "<button" not in body.lower()


def test_v37_8_is_registered_through_analytic_review_chain():
    root = Path(__file__).resolve().parents[1]
    chain = (root / "src/socmint/analytic_review_routes_v30_0.py").read_text(
        encoding="utf-8"
    )
    assert "register_operational_case_intelligence_workspace_routes_v37_8" in chain
    assert "register_operational_case_intelligence_workspace_routes_v37_8(app)" in chain
