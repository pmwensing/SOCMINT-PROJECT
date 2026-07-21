from pathlib import Path

from flask import Flask

from src.socmint import public_discovery_capture_workspace_routes_v38_8 as routes


def _payload():
    return {
        "status": "ready",
        "read_only": True,
        "summary": {
            "discovery_request_count": 1,
            "blocked_gate_count": 1,
            "capture_triage_count": 1,
            "uncertain_execution_count": 1,
        },
        "findings": [
            {
                "key": "blocked_discovery_gate",
                "count": 1,
                "severity": "block",
                "message": "The request is blocked.",
                "next_action": "Do not execute it.",
            },
            {
                "key": "execution_outcome_uncertain",
                "count": 1,
                "severity": "high",
                "message": "The execution outcome is uncertain.",
                "next_action": "Use read-only recovery review.",
            },
        ],
        "capability_inventory": [
            {
                "slice": "v38.5",
                "capability": "official public HTTP capture",
                "execution_mode": "operator_confirmed_live_network",
            },
            {
                "slice": "v38.6.4",
                "capability": "production enablement",
                "execution_mode": "certification_bound_single_use",
            },
        ],
        "gate_decision_inventory": [
            {
                "gate_decision_id": "gate-a",
                "decision": "block",
                "decision_blockers": ["robots_allow_required"],
                "live_network_eligible": False,
            }
        ],
        "production_enablement_inventory": [
            {
                "production_enablement_id": "enablement-a",
                "enablement_state": "claimed",
                "case_id": "case-a",
                "approved_domain": "records.example.test",
                "expires_at": "2026-07-21T22:00:00Z",
                "single_use": True,
                "automatic_execution": False,
                "automatic_retry": False,
            }
        ],
        "capture_triage_inventory": [
            {
                "capture_triage_id": "triage-a",
                "case_id": "case-a",
                "counts": {"support_eligible": 1},
                "unconfirmed_mirror_proposal_count": 1,
                "factual_significance_assigned": False,
                "causation_assigned": False,
            }
        ],
        "uncertain_execution_inventory": [
            {
                "execution_id": "execution-a",
                "governance_action": "execute_browsertrix_production_capture",
                "state": "uncertain",
                "ledger_consistent": True,
                "automatic_retry": False,
                "delegate_invocation_available": False,
            }
        ],
    }


def _app(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    app = Flask(__name__, template_folder=str(root / "src/socmint/templates"))
    app.secret_key = "v38-8-route-secret"

    @app.get("/", endpoint="dashboard.index")
    def index():
        return "index"

    @app.get("/login", endpoint="dashboard.login")
    def login():
        return "login"

    @app.get("/logout", endpoint="dashboard.logout")
    def logout():
        return "logout"

    routes.register_public_discovery_capture_workspace_routes_v38_8(app)
    monkeypatch.setattr(routes, "actor_is_administrator", lambda actor: actor == "admin")
    monkeypatch.setattr(routes, "build_public_discovery_capture_workspace", _payload)
    return app


def _login(client, user):
    with client.session_transaction() as state:
        state["user"] = user
        state["is_admin"] = user == "admin"


def test_v38_8_workspace_requires_administrator(monkeypatch):
    client = _app(monkeypatch).test_client()
    assert client.get("/public-discovery-capture").status_code == 302
    assert client.get("/api/v1/public-discovery-capture/workspace").status_code == 401
    _login(client, "viewer")
    assert client.get("/public-discovery-capture").status_code == 403
    assert client.get("/api/v1/public-discovery-capture/workspace").status_code == 403
    _login(client, "admin")
    assert client.get("/public-discovery-capture").status_code == 200
    response = client.get("/api/v1/public-discovery-capture/workspace")
    assert response.status_code == 200
    assert response.get_json()["read_only"] is True


def test_v38_8_template_is_explicitly_safe_and_read_only(monkeypatch):
    client = _app(monkeypatch).test_client()
    _login(client, "admin")
    body = client.get("/public-discovery-capture").get_data(as_text=True)
    for marker in (
        'data-public-discovery-capture-workspace="v38.8"',
        'data-read-only="true"',
        'data-safe-projection-only="true"',
        'data-raw-content-exposed="false"',
        'data-credentials-exposed="false"',
        'data-cookies-exposed="false"',
        'data-private-storage-paths-exposed="false"',
        'data-runtime-commands-exposed="false"',
        'data-automatic-collection="false"',
        'data-automatic-retry="false"',
        'data-automatic-artifact-acceptance="false"',
        'data-automatic-source-independence="false"',
        'data-automatic-observation-promotion="false"',
        'data-automatic-truth-assignment="false"',
        'data-automatic-entity-merge="false"',
        'data-automatic-claim-approval="false"',
        'data-automatic-dossier-mutation="false"',
        'data-automatic-import-staging="false"',
        'data-automatic-export="false"',
        'data-automatic-publication="false"',
        'data-write-actions="none"',
        'data-execution-recovery="true"',
        'data-capture-provenance="true"',
        'data-duplicate-change-triage="true"',
        'data-v37-handoff-visibility="true"',
        'data-finding-key="blocked_discovery_gate"',
        'data-finding-key="execution_outcome_uncertain"',
        'data-gate-decision="block"',
        'data-live-network-eligible="false"',
        'data-enablement-state="claimed"',
        'data-single-use="true"',
        'data-automatic-execution="false"',
        'data-capture-triage="triage-a"',
        'data-factual-significance-assigned="false"',
        'data-causation-assigned="false"',
        'data-execution-state="uncertain"',
        'data-delegate-invocation-available="false"',
    ):
        assert marker in body
    lowered = body.lower()
    for forbidden in (
        "<form",
        "<button",
        'method="post"',
        'name="collect"',
        'name="execute"',
        'name="retry"',
        'name="accept_artifact"',
        'name="assess_independence"',
        'name="promote"',
        'name="merge"',
        'name="approve"',
        'name="mutate_dossier"',
        'name="export"',
        'name="publish"',
    ):
        assert forbidden not in lowered


def test_v38_8_is_registered_through_analytic_review_chain():
    root = Path(__file__).resolve().parents[1]
    chain = (root / "src/socmint/analytic_review_routes_v30_0.py").read_text(
        encoding="utf-8"
    )
    assert "register_public_discovery_capture_workspace_routes_v38_8" in chain
    assert "register_public_discovery_capture_workspace_routes_v38_8(app)" in chain
