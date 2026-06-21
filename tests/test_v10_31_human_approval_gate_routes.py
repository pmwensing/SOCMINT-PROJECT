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
from socmint.v10_30_case_delivery_registry import build_case_delivery_registry
from socmint.v10_31_human_approval_gate_routes import (
    register_v10_31_human_approval_gate_routes,
)


def app_client():
    app = Flask(__name__)
    register_v10_31_human_approval_gate_routes(app)
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
        delivery_index(), bundle_name="Route Approval"
    )
    workspace = build_final_delivery_workspace_from_bundle(bundle)
    console = build_operator_console_from_workspace(workspace)
    audit_trail = build_final_delivery_audit_trail_from_console(console)
    capsule = build_final_delivery_evidence_capsule_from_audit_trail(audit_trail)
    pack = build_final_delivery_capsule_export_pack(capsule)
    return build_final_delivery_dashboard_api_from_pack(pack)


def registry():
    return build_case_delivery_registry("case-123", [dashboard()])


def test_approval_gate_route_accepts_registry_shape():
    client = app_client()
    response = client.post(
        "/api/v1/v10/final-delivery/cases/case-123/approval-gate",
        json={
            "registry": registry(),
            "decision": "approved",
            "operator": "analyst",
            "notes": "Approved.",
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["schema"] == "socmint.v10_31.human_approval_gate"
    assert data["decision"] == "approved"
    assert data["operator"] == "analyst"
    assert data["found"] is True
    assert "record_delivery" in data["allowed_actions"]


def test_approval_gate_route_accepts_index_shape():
    client = app_client()
    response = client.post(
        "/api/v1/v10/final-delivery/cases/case-123/approval-gate",
        json={
            "index": delivery_index(),
            "bundle_name": "Index Route Approval",
            "decision": "approved",
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["decision"] == "approved"
    assert data["delivery"]["bundle_name"] == "index-route-approval"
    assert data["found"] is True


def test_summary_route_returns_summary_only():
    client = app_client()
    response = client.post(
        "/api/v1/v10/final-delivery/cases/case-123/approval-gate/summary",
        json={
            "registry": registry(),
            "decision": "needs_correction",
            "notes": "Fix missing item.",
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["schema"] == "socmint.v10_31.human_approval_gate.summary"
    assert data["decision"] == "needs_correction"
    assert "registry" not in data
    assert "delivery" not in data
    assert "record_delivery" in data["blocked_actions"]


def test_missing_delivery_route_returns_404():
    client = app_client()
    response = client.post(
        "/api/v1/v10/final-delivery/cases/case-123/approval-gate",
        json={"registry": registry(), "delivery_id": "missing", "decision": "approved"},
    )

    assert response.status_code == 404
    assert response.get_json()["found"] is False


def test_missing_summary_route_returns_404():
    client = app_client()
    response = client.post(
        "/api/v1/v10/final-delivery/cases/case-123/approval-gate/summary",
        json={"registry": registry(), "delivery_id": "missing", "decision": "approved"},
    )

    assert response.status_code == 404
    assert response.get_json()["found"] is False


def test_no_connector_execution_function_is_called(monkeypatch):
    import socmint.v10_31_human_approval_gate as approval_module

    def explode(*_args, **_kwargs):
        raise AssertionError("connector execution must not happen")

    monkeypatch.setattr(approval_module, "execute_connector", explode, raising=False)
    client = app_client()
    response = client.post(
        "/api/v1/v10/final-delivery/cases/case-123/approval-gate",
        json={"index": delivery_index()},
    )

    assert response.status_code == 200
    assert response.get_json()["found"] is True
