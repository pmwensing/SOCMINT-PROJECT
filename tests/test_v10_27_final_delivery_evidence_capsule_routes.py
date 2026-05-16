from __future__ import annotations

from flask import Flask

from socmint.dossier_finalization_master_delivery_export_bundle_v7_5_14 import build_master_delivery_export_bundle
from socmint.dossier_finalization_master_delivery_index_v7_5_13 import build_master_delivery_index
from socmint.v10_24_final_delivery_workspace import build_final_delivery_workspace_from_bundle
from socmint.v10_25_final_delivery_operator_console import build_operator_console_from_workspace
from socmint.v10_26_final_delivery_audit_trail import build_final_delivery_audit_trail_from_console
from socmint.v10_27_final_delivery_evidence_capsule_routes import register_v10_27_final_delivery_evidence_capsule_routes


def app_client():
    app = Flask(__name__)
    register_v10_27_final_delivery_evidence_capsule_routes(app)
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


def audit_trail():
    bundle = build_master_delivery_export_bundle(delivery_index(), bundle_name="Route Capsule")
    workspace = build_final_delivery_workspace_from_bundle(bundle)
    console = build_operator_console_from_workspace(workspace)
    return build_final_delivery_audit_trail_from_console(console)


def test_capsule_route_accepts_audit_trail_shape():
    client = app_client()
    response = client.post("/api/v1/v10/final-delivery/evidence-capsule", json={"audit_trail": audit_trail()})

    assert response.status_code == 200
    data = response.get_json()
    assert data["schema"] == "socmint.v10_27.final_delivery_evidence_capsule"
    assert data["readiness"] == "ready"
    assert data["bundle_name"] == "route-capsule"
    assert data["operator_receipt"]["export_available"] is True


def test_capsule_route_accepts_index_shape():
    client = app_client()
    response = client.post(
        "/api/v1/v10/final-delivery/evidence-capsule",
        json={"index": delivery_index(), "bundle_name": "Index Route Capsule"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["readiness"] == "ready"
    assert data["bundle_name"] == "index-route-capsule"
    assert data["package_files"]


def test_summary_route_returns_compact_summary_only():
    client = app_client()
    response = client.post("/api/v1/v10/final-delivery/evidence-capsule/summary", json={"audit_trail": audit_trail()})

    assert response.status_code == 200
    data = response.get_json()
    assert data["schema"] == "socmint.v10_27.final_delivery_evidence_capsule.summary"
    assert data["readiness"] == "ready"
    assert data["bundle_name"] == "route-capsule"
    assert "audit_trail" not in data
    assert "console" not in data
    assert "workspace" not in data


def test_summary_route_accepts_index_shape():
    client = app_client()
    response = client.post(
        "/api/v1/v10/final-delivery/evidence-capsule/summary",
        json={"index": delivery_index(), "bundle_name": "Summary Route"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["bundle_name"] == "summary-route"
    assert data["export_available"] is True


def test_no_connector_execution_function_is_called(monkeypatch):
    import socmint.v10_27_final_delivery_evidence_capsule as capsule_module

    def explode(*_args, **_kwargs):
        raise AssertionError("connector execution must not happen")

    monkeypatch.setattr(capsule_module, "execute_connector", explode, raising=False)
    client = app_client()
    response = client.post("/api/v1/v10/final-delivery/evidence-capsule", json={"index": delivery_index()})

    assert response.status_code == 200
    assert response.get_json()["readiness"] == "ready"
