from __future__ import annotations

from flask import Flask

from socmint.dossier_finalization_master_delivery_export_bundle_v7_5_14 import build_master_delivery_export_bundle
from socmint.dossier_finalization_master_delivery_index_v7_5_13 import build_master_delivery_index
from socmint.v10_24_final_delivery_workspace import build_final_delivery_workspace_from_bundle
from socmint.v10_25_final_delivery_operator_console import build_operator_console_from_workspace
from socmint.v10_26_final_delivery_audit_trail import build_final_delivery_audit_trail_from_console
from socmint.v10_27_final_delivery_evidence_capsule import build_final_delivery_evidence_capsule_from_audit_trail
from socmint.v10_28_final_delivery_capsule_export_pack import build_final_delivery_capsule_export_pack
from socmint.v10_29_final_delivery_dashboard_api_routes import register_v10_29_final_delivery_dashboard_api_routes

EXPECTED_ACTIONS = {
    "console",
    "audit_trail",
    "evidence_capsule",
    "evidence_capsule_summary",
    "export_pack",
    "export_zip",
}


def app_client():
    app = Flask(__name__)
    register_v10_29_final_delivery_dashboard_api_routes(app)
    return app.test_client()


def verification_report():
    return {
        "schema": "socmint.v7_5_12.dossier_finalization_closeout_export_verification",
        "status": "verified",
        "verified": True,
        "failure_count": 0,
        "warning_count": 0,
        "required_files": ["README.md", "closeout_report.json"],
        "present_files": ["README.md", "closeout_report.json"],
        "missing_files": [],
        "unexpected_files": [],
        "manifest": {"file_count": 5, "files": []},
        "closeout_action": "closeout_ready",
        "verification_status": "verified",
        "failures": [],
        "warnings": [],
        "summary": {"status": "verified", "verified": True},
    }


def delivery_index():
    return build_master_delivery_index(verification_report(), operator="analyst", notes="Ready.")


def export_pack():
    bundle = build_master_delivery_export_bundle(delivery_index(), bundle_name="Route Dashboard")
    workspace = build_final_delivery_workspace_from_bundle(bundle)
    console = build_operator_console_from_workspace(workspace)
    audit_trail = build_final_delivery_audit_trail_from_console(console)
    capsule = build_final_delivery_evidence_capsule_from_audit_trail(audit_trail)
    return build_final_delivery_capsule_export_pack(capsule)


def test_dashboard_route_accepts_pack_shape():
    client = app_client()
    response = client.post("/api/v1/v10/final-delivery/dashboard", json={"pack": export_pack()})

    assert response.status_code == 200
    data = response.get_json()
    assert data["schema"] == "socmint.v10_29.final_delivery_dashboard_api"
    assert data["readiness"] == "ready"
    assert data["bundle_name"] == "route-dashboard"
    assert data["pack_id"]
    assert data["export"]["available"] is True


def test_dashboard_route_accepts_index_shape():
    client = app_client()
    response = client.post(
        "/api/v1/v10/final-delivery/dashboard",
        json={"index": delivery_index(), "bundle_name": "Index Route Dashboard"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["readiness"] == "ready"
    assert data["bundle_name"] == "index-route-dashboard"
    assert data["status_cards"]


def test_actions_route_returns_action_list_only():
    client = app_client()
    response = client.post("/api/v1/v10/final-delivery/dashboard/actions", json={"pack": export_pack()})

    assert response.status_code == 200
    data = response.get_json()
    assert set(data) == {"api_actions"}
    assert {action["id"] for action in data["api_actions"]} == EXPECTED_ACTIONS


def test_actions_route_accepts_index_shape():
    client = app_client()
    response = client.post(
        "/api/v1/v10/final-delivery/dashboard/actions",
        json={"index": delivery_index(), "bundle_name": "Action Index"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert {action["id"] for action in data["api_actions"]} == EXPECTED_ACTIONS


def test_no_connector_execution_function_is_called(monkeypatch):
    import socmint.v10_29_final_delivery_dashboard_api as dashboard_module

    def explode(*_args, **_kwargs):
        raise AssertionError("connector execution must not happen")

    monkeypatch.setattr(dashboard_module, "execute_connector", explode, raising=False)
    client = app_client()
    response = client.post("/api/v1/v10/final-delivery/dashboard", json={"index": delivery_index()})

    assert response.status_code == 200
    assert response.get_json()["readiness"] == "ready"
