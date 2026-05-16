from __future__ import annotations

from copy import deepcopy

from socmint.dossier_finalization_master_delivery_export_bundle_v7_5_14 import build_master_delivery_export_bundle
from socmint.dossier_finalization_master_delivery_index_v7_5_13 import build_master_delivery_index
from socmint.v10_24_final_delivery_workspace import build_final_delivery_workspace_from_bundle
from socmint.v10_25_final_delivery_operator_console import build_operator_console_from_workspace
from socmint.v10_26_final_delivery_audit_trail import build_final_delivery_audit_receipt_from_request
from socmint.v10_26_final_delivery_audit_trail import build_final_delivery_audit_trail_from_console
from socmint.v10_26_final_delivery_audit_trail import build_final_delivery_audit_trail_from_request


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
                "path": "master_delivery_index.json",
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
                "path": "master_delivery_index.json",
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


def workspace(status="verified"):
    bundle = build_master_delivery_export_bundle(delivery_index(status), bundle_name="Audit Package")
    return build_final_delivery_workspace_from_bundle(bundle)


def console(status="verified"):
    return build_operator_console_from_workspace(workspace(status))


def test_builds_audit_trail_from_ready_console():
    audit = build_final_delivery_audit_trail_from_console(console())

    assert audit["schema"] == "socmint.v10_26.final_delivery_audit_trail"
    assert audit["version"] == "v10.26.0"
    assert audit["readiness"] == "ready"
    assert audit["delivery_action"] == "deliver_ready"
    assert audit["package_ready"] is True
    assert audit["bundle_name"] == "audit-package"
    assert audit["file_count"] == 5
    assert audit["export_available"] is True
    assert audit["audit_id"]


def test_builds_audit_trail_from_review_required_console():
    audit = build_final_delivery_audit_trail_from_console(console("needs_human_review"))

    assert audit["readiness"] == "review_required"
    assert audit["delivery_action"] == "human_review_required"
    assert audit["export_available"] is False
    assert audit["finding_count"] == 1


def test_builds_audit_trail_from_blocked_console():
    audit = build_final_delivery_audit_trail_from_console(console("failed"))

    assert audit["readiness"] == "blocked"
    assert audit["delivery_action"] == "regenerate_export"
    assert audit["export_available"] is False
    assert audit["finding_count"] == 1


def test_audit_id_is_stable_for_equivalent_console_content():
    first = build_final_delivery_audit_trail_from_console(console())
    second = build_final_delivery_audit_trail_from_console(console())

    assert first["audit_id"] == second["audit_id"]
    assert first["generated_at"] != second["generated_at"] or first["audit_id"] == second["audit_id"]


def test_receipt_contains_required_summary_fields():
    audit = build_final_delivery_audit_trail_from_console(console())
    receipt = audit["operator_receipt"]

    assert receipt["audit_id"] == audit["audit_id"]
    assert receipt["readiness"] == "ready"
    assert receipt["delivery_action"] == "deliver_ready"
    assert receipt["bundle_name"] == "audit-package"
    assert receipt["export_available"] is True
    assert receipt["command_count"] == len(audit["console"]["commands"])


def test_builds_audit_from_request_console_shape():
    payload = {"console": console()}
    audit = build_final_delivery_audit_trail_from_request(payload)

    assert audit["readiness"] == "ready"
    assert audit["operator_receipt"]["bundle_name"] == "audit-package"


def test_builds_audit_from_request_index_shape():
    audit = build_final_delivery_audit_trail_from_request({"index": delivery_index(), "bundle_name": "Index Audit"})

    assert audit["readiness"] == "ready"
    assert audit["bundle_name"] == "index-audit"


def test_receipt_from_request_returns_receipt_only():
    receipt = build_final_delivery_audit_receipt_from_request({"console": console()})

    assert "console" not in receipt
    assert receipt["bundle_name"] == "audit-package"
    assert receipt["export_available"] is True


def test_input_payload_is_not_mutated():
    payload = {"console": console()}
    original = deepcopy(payload)

    build_final_delivery_audit_trail_from_request(payload)

    assert payload == original


def test_no_connector_execution_function_is_called(monkeypatch):
    import socmint.v10_26_final_delivery_audit_trail as audit_module

    def explode(*_args, **_kwargs):
        raise AssertionError("connector execution must not happen")

    monkeypatch.setattr(audit_module, "execute_connector", explode, raising=False)

    audit = build_final_delivery_audit_trail_from_request({"index": delivery_index()})

    assert audit["readiness"] == "ready"
