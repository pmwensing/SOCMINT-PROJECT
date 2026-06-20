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
from socmint.v10_27_final_delivery_evidence_capsule import (
    build_final_delivery_evidence_capsule_from_request,
)
from socmint.v10_27_final_delivery_evidence_capsule import (
    build_final_delivery_evidence_capsule_summary_from_request,
)


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
    return build_master_delivery_index(
        verification_report(status), operator="analyst", notes="Ready."
    )


def audit_trail(status="verified"):
    bundle = build_master_delivery_export_bundle(
        delivery_index(status), bundle_name="Capsule Package"
    )
    workspace = build_final_delivery_workspace_from_bundle(bundle)
    console = build_operator_console_from_workspace(workspace)
    return build_final_delivery_audit_trail_from_console(console)


def test_builds_capsule_from_ready_audit_trail():
    capsule = build_final_delivery_evidence_capsule_from_audit_trail(audit_trail())

    assert capsule["schema"] == "socmint.v10_27.final_delivery_evidence_capsule"
    assert capsule["version"] == "v10.27.0"
    assert capsule["readiness"] == "ready"
    assert capsule["bundle_name"] == "capsule-package"
    assert capsule["capsule_id"]
    assert capsule["operator_receipt"]["export_available"] is True


def test_builds_capsule_from_review_required_audit_trail():
    capsule = build_final_delivery_evidence_capsule_from_audit_trail(
        audit_trail("needs_human_review")
    )

    assert capsule["readiness"] == "review_required"
    assert capsule["operator_receipt"]["export_available"] is False
    assert capsule["summary"]["export_available"] is False


def test_builds_capsule_from_blocked_audit_trail():
    capsule = build_final_delivery_evidence_capsule_from_audit_trail(
        audit_trail("failed")
    )

    assert capsule["readiness"] == "blocked"
    assert capsule["operator_receipt"]["export_available"] is False
    assert capsule["summary"]["readiness"] == "blocked"


def test_capsule_id_is_stable_for_equivalent_content():
    first = build_final_delivery_evidence_capsule_from_audit_trail(audit_trail())
    second = build_final_delivery_evidence_capsule_from_audit_trail(audit_trail())

    assert first["capsule_id"] == second["capsule_id"]


def test_capsule_includes_all_review_artifacts():
    capsule = build_final_delivery_evidence_capsule_from_audit_trail(audit_trail())

    assert capsule["package_files"]
    assert capsule["cards"]
    assert capsule["commands"]
    assert capsule["operator_receipt"]
    assert capsule["audit_trail"]
    assert capsule["workspace"]
    assert capsule["console"]


def test_summary_is_compact():
    capsule = build_final_delivery_evidence_capsule_from_audit_trail(audit_trail())
    summary = capsule["summary"]

    assert summary["schema"] == "socmint.v10_27.final_delivery_evidence_capsule.summary"
    assert summary["capsule_id"] == capsule["capsule_id"]
    assert summary["readiness"] == "ready"
    assert "audit_trail" not in summary
    assert "console" not in summary
    assert "workspace" not in summary


def test_builds_capsule_from_request_audit_trail_shape():
    trail = audit_trail()
    capsule = build_final_delivery_evidence_capsule_from_request({"audit_trail": trail})

    assert capsule["readiness"] == "ready"
    assert capsule["audit_trail"]["audit_id"] == trail["audit_id"]


def test_builds_capsule_from_request_index_shape():
    capsule = build_final_delivery_evidence_capsule_from_request(
        {"index": delivery_index(), "bundle_name": "Index Capsule"}
    )

    assert capsule["readiness"] == "ready"
    assert capsule["bundle_name"] == "index-capsule"


def test_summary_from_request_returns_summary_only():
    summary = build_final_delivery_evidence_capsule_summary_from_request(
        {"audit_trail": audit_trail()}
    )

    assert summary["readiness"] == "ready"
    assert "audit_trail" not in summary
    assert "operator_receipt" not in summary


def test_input_payload_is_not_mutated():
    payload = {"audit_trail": audit_trail()}
    original = deepcopy(payload)

    build_final_delivery_evidence_capsule_from_request(payload)

    assert payload == original


def test_no_connector_execution_function_is_called(monkeypatch):
    import socmint.v10_27_final_delivery_evidence_capsule as capsule_module

    def explode(*_args, **_kwargs):
        raise AssertionError("connector execution must not happen")

    monkeypatch.setattr(capsule_module, "execute_connector", explode, raising=False)

    capsule = build_final_delivery_evidence_capsule_from_request(
        {"index": delivery_index()}
    )

    assert capsule["readiness"] == "ready"
