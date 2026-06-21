from __future__ import annotations

from flask import Flask

from socmint.dossier_finalization_master_delivery_export_bundle_v7_5_14 import (
    build_master_delivery_export_bundle,
)
from socmint.dossier_finalization_master_delivery_index_v7_5_13 import (
    build_master_delivery_index,
)
from socmint.v10_24_final_delivery_workspace import (
    build_final_delivery_workspace_from_bundle,
)
from socmint.v10_25_final_delivery_operator_console import (
    build_operator_console_from_workspace,
)
from socmint.v10_26_final_delivery_audit_trail_routes import (
    register_v10_26_final_delivery_audit_trail_routes,
)


def app_client():
    app = Flask(__name__)
    register_v10_26_final_delivery_audit_trail_routes(app)
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
    return build_master_delivery_index(
        verification_report(), operator="analyst", notes="Ready."
    )


def console():
    bundle = build_master_delivery_export_bundle(
        delivery_index(), bundle_name="Route Audit"
    )
    workspace = build_final_delivery_workspace_from_bundle(bundle)
    return build_operator_console_from_workspace(workspace)


def test_audit_trail_route_accepts_console_shape():
    client = app_client()
    response = client.post(
        "/api/v1/v10/final-delivery/audit-trail", json={"console": console()}
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["schema"] == "socmint.v10_26.final_delivery_audit_trail"
    assert data["readiness"] == "ready"
    assert data["delivery_action"] == "deliver_ready"
    assert data["operator_receipt"]["bundle_name"] == "route-audit"


def test_audit_trail_route_accepts_index_shape():
    client = app_client()
    response = client.post(
        "/api/v1/v10/final-delivery/audit-trail",
        json={"index": delivery_index(), "bundle_name": "Index Route Audit"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["readiness"] == "ready"
    assert data["bundle_name"] == "index-route-audit"
    assert data["export_available"] is True


def test_audit_receipt_route_returns_receipt_only():
    client = app_client()
    response = client.post(
        "/api/v1/v10/final-delivery/audit-receipt", json={"console": console()}
    )

    assert response.status_code == 200
    data = response.get_json()
    assert "console" not in data
    assert data["readiness"] == "ready"
    assert data["delivery_action"] == "deliver_ready"
    assert data["bundle_name"] == "route-audit"
    assert data["export_available"] is True
    assert data["audit_id"]


def test_audit_receipt_route_accepts_index_shape():
    client = app_client()
    response = client.post(
        "/api/v1/v10/final-delivery/audit-receipt",
        json={"index": delivery_index(), "bundle_name": "Receipt Index"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["bundle_name"] == "receipt-index"
    assert data["command_count"] == 3


def test_no_connector_execution_function_is_called(monkeypatch):
    import socmint.v10_26_final_delivery_audit_trail as audit_module

    def explode(*_args, **_kwargs):
        raise AssertionError("connector execution must not happen")

    monkeypatch.setattr(audit_module, "execute_connector", explode, raising=False)
    client = app_client()
    response = client.post(
        "/api/v1/v10/final-delivery/audit-trail", json={"index": delivery_index()}
    )

    assert response.status_code == 200
    assert response.get_json()["readiness"] == "ready"
