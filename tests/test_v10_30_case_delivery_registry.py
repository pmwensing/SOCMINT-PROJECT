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
from socmint.v10_30_case_delivery_registry import (
    build_case_delivery_registry_from_request,
)
from socmint.v10_30_case_delivery_registry import (
    build_case_delivery_summaries_from_request,
)
from socmint.v10_30_case_delivery_registry import delivery_id_for_dashboard
from socmint.v10_30_case_delivery_registry import get_case_delivery_from_request
from socmint.v10_30_case_delivery_registry import get_delivery_by_id
from socmint.v10_30_case_delivery_registry import list_delivery_summaries


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
                "path": "registry.json",
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
                "path": "registry.json",
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


def dashboard(status="verified", bundle_name="Registry Pack"):
    bundle = build_master_delivery_export_bundle(
        delivery_index(status), bundle_name=bundle_name
    )
    workspace = build_final_delivery_workspace_from_bundle(bundle)
    console = build_operator_console_from_workspace(workspace)
    audit_trail = build_final_delivery_audit_trail_from_console(console)
    capsule = build_final_delivery_evidence_capsule_from_audit_trail(audit_trail)
    pack = build_final_delivery_capsule_export_pack(capsule)
    return build_final_delivery_dashboard_api_from_pack(pack)


def test_builds_registry_from_one_ready_dashboard():
    registry = build_case_delivery_registry("case-123", [dashboard()])

    assert registry["schema"] == "socmint.v10_30.case_delivery_registry"
    assert registry["version"] == "v10.30.0"
    assert registry["case_id"] == "case-123"
    assert registry["delivery_count"] == 1
    assert registry["latest_readiness"] == "ready"
    assert registry["latest_delivery_id"] == registry["deliveries"][0]["delivery_id"]


def test_builds_registry_from_multiple_dashboard_states():
    registry = build_case_delivery_registry(
        "case-123",
        [dashboard("verified", "Ready"), dashboard("needs_human_review", "Review")],
    )

    assert registry["delivery_count"] == 2
    assert registry["latest_readiness"] == "review_required"
    assert registry["summary"]["readiness_counts"]["ready"] == 1
    assert registry["summary"]["readiness_counts"]["review_required"] == 1


def test_delivery_ids_are_stable_for_equivalent_dashboard_and_case():
    first = dashboard()
    second = deepcopy(first)

    assert delivery_id_for_dashboard("case-123", first) == delivery_id_for_dashboard(
        "case-123", second
    )


def test_lists_compact_summaries():
    registry = build_case_delivery_registry("case-123", [dashboard()])
    summaries = list_delivery_summaries(registry)

    assert len(summaries) == 1
    assert summaries[0]["delivery_id"] == registry["deliveries"][0]["delivery_id"]
    assert "dashboard" not in summaries[0]


def test_retrieves_delivery_by_id():
    registry = build_case_delivery_registry("case-123", [dashboard()])
    delivery_id = registry["deliveries"][0]["delivery_id"]

    found = get_delivery_by_id(registry, delivery_id)

    assert found is not None
    assert found["delivery_id"] == delivery_id
    assert found["dashboard"]["readiness"] == "ready"


def test_builds_registry_from_request_dashboard_shape():
    source = dashboard()
    registry = build_case_delivery_registry_from_request(
        "case-123", {"dashboard": source}
    )

    assert registry["delivery_count"] == 1
    assert registry["deliveries"][0]["pack_id"] == source["pack_id"]


def test_builds_registry_from_request_index_shape():
    registry = build_case_delivery_registry_from_request(
        "case-123", {"index": delivery_index(), "bundle_name": "Index Registry"}
    )

    assert registry["delivery_count"] == 1
    assert registry["latest_readiness"] == "ready"
    assert registry["deliveries"][0]["bundle_name"] == "index-registry"


def test_summaries_from_request_returns_summaries_only():
    summaries = build_case_delivery_summaries_from_request(
        "case-123", {"dashboard": dashboard()}
    )

    assert len(summaries) == 1
    assert "dashboard" not in summaries[0]


def test_get_case_delivery_from_request_returns_selected_delivery():
    source = dashboard()
    delivery_id = delivery_id_for_dashboard("case-123", source)

    found = get_case_delivery_from_request(
        "case-123", {"delivery_id": delivery_id, "dashboard": source}
    )

    assert found is not None
    assert found["delivery_id"] == delivery_id


def test_input_payload_is_not_mutated():
    payload = {"dashboard": dashboard()}
    original = deepcopy(payload)

    build_case_delivery_registry_from_request("case-123", payload)

    assert payload == original


def test_no_connector_execution_function_is_called(monkeypatch):
    import socmint.v10_30_case_delivery_registry as registry_module

    def explode(*_args, **_kwargs):
        raise AssertionError("connector execution must not happen")

    monkeypatch.setattr(registry_module, "execute_connector", explode, raising=False)

    registry = build_case_delivery_registry_from_request(
        "case-123", {"index": delivery_index()}
    )

    assert registry["latest_readiness"] == "ready"
