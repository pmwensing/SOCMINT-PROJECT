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
from socmint.v10_26_final_delivery_audit_trail import (
    build_final_delivery_audit_trail_from_console,
)
from socmint.v10_27_final_delivery_evidence_capsule import (
    build_final_delivery_evidence_capsule_from_audit_trail,
)
from socmint.v10_28_final_delivery_capsule_export_pack import (
    build_final_delivery_capsule_export_pack,
)
from socmint.v10_29_final_delivery_dashboard_api import (
    build_final_delivery_dashboard_api_from_pack,
)
from socmint.v10_30_case_delivery_registry import delivery_id_for_dashboard
from socmint.v10_30_case_delivery_registry_routes import (
    register_v10_30_case_delivery_registry_routes,
)


def app_client():
    app = Flask(__name__)
    register_v10_30_case_delivery_registry_routes(app)
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


def dashboard():
    bundle = build_master_delivery_export_bundle(
        delivery_index(), bundle_name="Route Registry"
    )
    workspace = build_final_delivery_workspace_from_bundle(bundle)
    console = build_operator_console_from_workspace(workspace)
    audit_trail = build_final_delivery_audit_trail_from_console(console)
    capsule = build_final_delivery_evidence_capsule_from_audit_trail(audit_trail)
    pack = build_final_delivery_capsule_export_pack(capsule)
    return build_final_delivery_dashboard_api_from_pack(pack)


def test_registry_route_accepts_dashboard_shape():
    client = app_client()
    response = client.post(
        "/api/v1/v10/final-delivery/cases/case-123/registry",
        json={"dashboard": dashboard()},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["schema"] == "socmint.v10_30.case_delivery_registry"
    assert data["case_id"] == "case-123"
    assert data["delivery_count"] == 1
    assert data["latest_readiness"] == "ready"


def test_registry_route_accepts_index_shape():
    client = app_client()
    response = client.post(
        "/api/v1/v10/final-delivery/cases/case-123/registry",
        json={"index": delivery_index(), "bundle_name": "Index Route Registry"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["delivery_count"] == 1
    assert data["deliveries"][0]["bundle_name"] == "index-route-registry"


def test_summaries_route_returns_summaries_only():
    client = app_client()
    response = client.post(
        "/api/v1/v10/final-delivery/cases/case-123/registry/summaries",
        json={"dashboard": dashboard()},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert set(data) == {"summaries"}
    assert len(data["summaries"]) == 1
    assert "dashboard" not in data["summaries"][0]


def test_delivery_route_returns_selected_delivery():
    client = app_client()
    source = dashboard()
    delivery_id = delivery_id_for_dashboard("case-123", source)
    response = client.post(
        "/api/v1/v10/final-delivery/cases/case-123/registry/delivery",
        json={"delivery_id": delivery_id, "dashboard": source},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["found"] is True
    assert data["delivery"]["delivery_id"] == delivery_id


def test_delivery_route_returns_404_when_missing():
    client = app_client()
    response = client.post(
        "/api/v1/v10/final-delivery/cases/case-123/registry/delivery",
        json={"delivery_id": "missing", "dashboard": dashboard()},
    )

    assert response.status_code == 404
    assert response.get_json()["found"] is False


def test_no_connector_execution_function_is_called(monkeypatch):
    import socmint.v10_30_case_delivery_registry as registry_module

    def explode(*_args, **_kwargs):
        raise AssertionError("connector execution must not happen")

    monkeypatch.setattr(registry_module, "execute_connector", explode, raising=False)
    client = app_client()
    response = client.post(
        "/api/v1/v10/final-delivery/cases/case-123/registry",
        json={"index": delivery_index()},
    )

    assert response.status_code == 200
    assert response.get_json()["latest_readiness"] == "ready"
