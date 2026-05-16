from __future__ import annotations

from copy import deepcopy

from socmint.dossier_finalization_master_delivery_export_bundle_v7_5_14 import build_master_delivery_export_bundle
from socmint.dossier_finalization_master_delivery_index_v7_5_13 import build_master_delivery_index
from socmint.v10_24_final_delivery_workspace import build_final_delivery_workspace_from_bundle
from socmint.v10_25_final_delivery_operator_console import build_operator_console_from_workspace
from socmint.v10_26_final_delivery_audit_trail import build_final_delivery_audit_trail_from_console
from socmint.v10_27_final_delivery_evidence_capsule import build_final_delivery_evidence_capsule_from_audit_trail
from socmint.v10_28_final_delivery_capsule_export_pack import build_final_delivery_capsule_export_pack
from socmint.v10_29_final_delivery_dashboard_api import build_final_delivery_dashboard_actions_from_request
from socmint.v10_29_final_delivery_dashboard_api import build_final_delivery_dashboard_api_from_pack
from socmint.v10_29_final_delivery_dashboard_api import build_final_delivery_dashboard_api_from_request

REQUIRED_CARD_TYPES = {
    "readiness",
    "evidence_capsule",
    "audit_receipt",
    "package_inventory",
    "export_pack",
}
EXPECTED_ACTIONS = {
    "console",
    "audit_trail",
    "evidence_capsule",
    "evidence_capsule_summary",
    "export_pack",
    "export_zip",
}


def verification_report(status="verified"):
    return {
        "schema": "socmint.v7_5_12.dossier_finalization_closeout_export_verification",
        "status": status,
        "verified": status == "verified",
        "failure_count": 1 if status == "failed" else 0,
        "warning_count": 1 if status == "needs_human_review" else 0,
        "required_files": ["README.md", "closeout_report.json"],
        "present_files": ["README.md", "closeout_report.json"],
        "missing_files": [],
        "unexpected_files": [],
        "manifest": {"file_count": 5, "files": []},
        "closeout_action": "closeout_ready" if status == "verified" else "regenerate_export",
        "verification_status": status,
        "failures": [
            {
                "severity": "fail",
                "code": "failed_export",
                "path": "dashboard.json",
                "detail": "Export failed.",
                "action": "Regenerate export.",
            }
        ]
        if status == "failed"
        else [],
        "warnings": [
            {
                "severity": "warn",
                "code": "review_required",
                "path": "dashboard.json",
                "detail": "Review required.",
                "action": "Review package.",
            }
        ]
        if status == "needs_human_review"
        else [],
        "summary": {"status": status, "verified": status == "verified"},
    }


def delivery_index(status="verified"):
    return build_master_delivery_index(verification_report(status), operator="analyst", notes="Ready.")


def export_pack(status="verified"):
    bundle = build_master_delivery_export_bundle(delivery_index(status), bundle_name="Dashboard Pack")
    workspace = build_final_delivery_workspace_from_bundle(bundle)
    console = build_operator_console_from_workspace(workspace)
    audit_trail = build_final_delivery_audit_trail_from_console(console)
    capsule = build_final_delivery_evidence_capsule_from_audit_trail(audit_trail)
    return build_final_delivery_capsule_export_pack(capsule)


def test_builds_dashboard_from_ready_export_pack():
    dashboard = build_final_delivery_dashboard_api_from_pack(export_pack())

    assert dashboard["schema"] == "socmint.v10_29.final_delivery_dashboard_api"
    assert dashboard["version"] == "v10.29.0"
    assert dashboard["readiness"] == "ready"
    assert dashboard["bundle_name"] == "dashboard-pack"
    assert dashboard["capsule_id"]
    assert dashboard["pack_id"]
    assert dashboard["export"]["available"] is True
    assert dashboard["export"]["zip_available"] is True


def test_builds_dashboard_from_review_required_export_pack():
    dashboard = build_final_delivery_dashboard_api_from_pack(export_pack("needs_human_review"))

    assert dashboard["readiness"] == "review_required"
    assert dashboard["export"]["available"] is True
    assert dashboard["export"]["zip_available"] is False


def test_builds_dashboard_from_blocked_export_pack():
    dashboard = build_final_delivery_dashboard_api_from_pack(export_pack("failed"))

    assert dashboard["readiness"] == "blocked"
    assert dashboard["export"]["available"] is True
    assert dashboard["export"]["zip_available"] is False


def test_status_cards_include_required_types():
    dashboard = build_final_delivery_dashboard_api_from_pack(export_pack())

    assert {card["type"] for card in dashboard["status_cards"]} == REQUIRED_CARD_TYPES


def test_api_actions_include_expected_routes():
    dashboard = build_final_delivery_dashboard_api_from_pack(export_pack())

    assert {action["id"] for action in dashboard["api_actions"]} == EXPECTED_ACTIONS
    assert {action["route"] for action in dashboard["api_actions"]} >= {
        "/api/v1/v10/final-delivery/console",
        "/api/v1/v10/final-delivery/audit-trail",
        "/api/v1/v10/final-delivery/evidence-capsule",
        "/api/v1/v10/final-delivery/evidence-capsule/summary",
        "/api/v1/v10/final-delivery/evidence-capsule/export",
        "/api/v1/v10/final-delivery/evidence-capsule/export.zip",
    }


def test_actions_from_request_returns_action_list_only():
    actions = build_final_delivery_dashboard_actions_from_request({"pack": export_pack()})

    assert isinstance(actions, list)
    assert {action["id"] for action in actions} == EXPECTED_ACTIONS


def test_builds_dashboard_from_request_pack_shape():
    pack = export_pack()
    dashboard = build_final_delivery_dashboard_api_from_request({"pack": pack})

    assert dashboard["pack_id"] == pack["pack_id"]
    assert dashboard["readiness"] == "ready"


def test_builds_dashboard_from_request_index_shape():
    dashboard = build_final_delivery_dashboard_api_from_request({"index": delivery_index(), "bundle_name": "Index Dashboard"})

    assert dashboard["readiness"] == "ready"
    assert dashboard["bundle_name"] == "index-dashboard"


def test_input_payload_is_not_mutated():
    payload = {"pack": export_pack()}
    original = deepcopy(payload)

    build_final_delivery_dashboard_api_from_request(payload)

    assert payload == original


def test_no_connector_execution_function_is_called(monkeypatch):
    import socmint.v10_29_final_delivery_dashboard_api as dashboard_module

    def explode(*_args, **_kwargs):
        raise AssertionError("connector execution must not happen")

    monkeypatch.setattr(dashboard_module, "execute_connector", explode, raising=False)

    dashboard = build_final_delivery_dashboard_api_from_request({"index": delivery_index()})

    assert dashboard["readiness"] == "ready"
