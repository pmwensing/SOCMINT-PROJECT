from __future__ import annotations

from copy import deepcopy

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
from socmint.v10_31_human_approval_gate import actions_for_decision
from socmint.v10_31_human_approval_gate import approval_id_for_decision
from socmint.v10_31_human_approval_gate import build_human_approval_gate
from socmint.v10_31_human_approval_gate import build_human_approval_gate_from_request
from socmint.v10_31_human_approval_gate import build_human_approval_summary_from_request
from socmint.v10_31_human_approval_gate import normalize_decision


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
        "closeout_action": "closeout_ready"
        if status == "verified"
        else "regenerate_export",
        "verification_status": status,
        "failures": [],
        "warnings": [],
        "summary": {"status": status, "verified": status == "verified"},
    }


def delivery_index(status="verified"):
    return build_master_delivery_index(
        verification_report(status), operator="analyst", notes="Ready."
    )


def dashboard(status="verified", bundle_name="Approval Pack"):
    bundle = build_master_delivery_export_bundle(
        delivery_index(status), bundle_name=bundle_name
    )
    workspace = build_final_delivery_workspace_from_bundle(bundle)
    console = build_operator_console_from_workspace(workspace)
    audit_trail = build_final_delivery_audit_trail_from_console(console)
    capsule = build_final_delivery_evidence_capsule_from_audit_trail(audit_trail)
    pack = build_final_delivery_capsule_export_pack(capsule)
    return build_final_delivery_dashboard_api_from_pack(pack)


def registry(status="verified"):
    return build_case_delivery_registry("case-123", [dashboard(status)])


def test_builds_pending_review_gate_from_latest_delivery():
    reg = registry()
    gate = build_human_approval_gate(case_id="case-123", registry=reg)

    assert gate["schema"] == "socmint.v10_31.human_approval_gate"
    assert gate["version"] == "v10.31.0"
    assert gate["case_id"] == "case-123"
    assert gate["delivery_id"] == reg["latest_delivery_id"]
    assert gate["decision"] == "pending_review"
    assert gate["found"] is True
    assert "review_delivery" in gate["allowed_actions"]
    assert "record_delivery" in gate["blocked_actions"]


def test_approved_gate_maps_allowed_and_blocked_actions():
    gate = build_human_approval_gate(
        case_id="case-123", registry=registry(), decision="approved", operator="analyst"
    )

    assert gate["decision"] == "approved"
    assert gate["allowed_actions"] == [
        "export_zip",
        "record_delivery",
        "archive_case_delivery",
    ]
    assert gate["blocked_actions"] == ["reject_delivery", "request_correction"]


def test_rejected_gate_maps_allowed_and_blocked_actions():
    gate = build_human_approval_gate(
        case_id="case-123", registry=registry(), decision="rejected"
    )

    assert gate["decision"] == "rejected"
    assert gate["allowed_actions"] == ["revise_delivery", "regenerate_export"]
    assert gate["blocked_actions"] == ["record_delivery", "archive_case_delivery"]


def test_needs_correction_gate_maps_allowed_and_blocked_actions():
    gate = build_human_approval_gate(
        case_id="case-123", registry=registry(), decision="needs_correction"
    )

    assert gate["decision"] == "needs_correction"
    assert gate["allowed_actions"] == [
        "revise_delivery",
        "rerun_registry",
        "request_review",
    ]
    assert gate["blocked_actions"] == ["record_delivery", "archive_case_delivery"]


def test_invalid_decision_normalizes_to_pending_review():
    assert normalize_decision("bad") == "pending_review"
    assert actions_for_decision("bad")["allowed"] == [
        "review_delivery",
        "approve_delivery",
        "reject_delivery",
        "request_correction",
    ]


def test_approval_ids_are_stable_for_equivalent_decision_content():
    first = approval_id_for_decision(
        case_id="case-123",
        delivery_id="delivery-1",
        decision="approved",
        operator="analyst",
        notes="ok",
    )
    second = approval_id_for_decision(
        case_id="case-123",
        delivery_id="delivery-1",
        decision="approved",
        operator="analyst",
        notes="ok",
    )

    assert first == second


def test_summary_contains_decision_delivery_actions_and_readiness():
    gate = build_human_approval_gate(
        case_id="case-123", registry=registry(), decision="approved", notes="Approved."
    )
    summary = gate["summary"]

    assert summary["schema"] == "socmint.v10_31.human_approval_gate.summary"
    assert summary["decision"] == "approved"
    assert summary["delivery_id"] == gate["delivery_id"]
    assert summary["readiness"] == "ready"
    assert summary["allowed_actions"] == gate["allowed_actions"]
    assert summary["blocked_actions"] == gate["blocked_actions"]


def test_builds_gate_from_request_registry_shape():
    reg = registry()
    gate = build_human_approval_gate_from_request(
        "case-123", {"registry": reg, "decision": "approved"}
    )

    assert gate["decision"] == "approved"
    assert gate["delivery_id"] == reg["latest_delivery_id"]


def test_builds_gate_from_request_index_shape():
    gate = build_human_approval_gate_from_request(
        "case-123",
        {
            "index": delivery_index(),
            "bundle_name": "Index Approval",
            "decision": "approved",
        },
    )

    assert gate["decision"] == "approved"
    assert gate["found"] is True
    assert gate["delivery"]["bundle_name"] == "index-approval"


def test_summary_from_request_returns_summary_only():
    summary = build_human_approval_summary_from_request(
        "case-123", {"registry": registry(), "decision": "approved"}
    )

    assert summary["decision"] == "approved"
    assert "registry" not in summary
    assert "delivery" not in summary


def test_missing_delivery_returns_not_found_gate():
    gate = build_human_approval_gate(
        case_id="case-123", registry=registry(), delivery_id="missing"
    )

    assert gate["found"] is False
    assert gate["delivery"] == {}
    assert gate["summary"]["found"] is False


def test_input_payload_is_not_mutated():
    payload = {"registry": registry(), "decision": "approved"}
    original = deepcopy(payload)

    build_human_approval_gate_from_request("case-123", payload)

    assert payload == original


def test_no_connector_execution_function_is_called(monkeypatch):
    import socmint.v10_31_human_approval_gate as approval_module

    def explode(*_args, **_kwargs):
        raise AssertionError("connector execution must not happen")

    monkeypatch.setattr(approval_module, "execute_connector", explode, raising=False)

    gate = build_human_approval_gate_from_request(
        "case-123", {"index": delivery_index()}
    )

    assert gate["found"] is True
