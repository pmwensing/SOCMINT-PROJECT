from __future__ import annotations

import io
import zipfile
from copy import deepcopy

from socmint.dossier_finalization_master_delivery_export_bundle_v7_5_14 import build_master_delivery_export_bundle
from socmint.dossier_finalization_master_delivery_index_v7_5_13 import build_master_delivery_index
from socmint.v10_24_final_delivery_workspace import build_final_delivery_bundle_from_request
from socmint.v10_24_final_delivery_workspace import build_final_delivery_export_zip_from_request
from socmint.v10_24_final_delivery_workspace import build_final_delivery_workspace_from_bundle
from socmint.v10_24_final_delivery_workspace import build_final_delivery_workspace_from_index
from socmint.v10_24_final_delivery_workspace import build_final_delivery_workspace_from_request
from socmint.v10_24_final_delivery_workspace import operator_actions_for_delivery

REQUIRED_FILES = {
    "README.md",
    "master_delivery_index.json",
    "master_delivery_index.md",
    "master_delivery_index_summary.json",
    "manifest.json",
}


def verification_report(status="verified", delivery_action="closeout_ready"):
    return {
        "schema": "socmint.v7_5_12.dossier_finalization_closeout_export_verification",
        "status": status,
        "verified": status == "verified",
        "failure_count": 0 if status != "failed" else 1,
        "warning_count": 1 if status == "needs_human_review" else 0,
        "required_files": ["README.md", "closeout_report.json"],
        "present_files": ["README.md", "closeout_report.json"],
        "missing_files": [],
        "unexpected_files": [],
        "manifest": {"file_count": 5, "files": []},
        "closeout_action": delivery_action,
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
    report = verification_report(status=status)
    return build_master_delivery_index(report, operator="analyst", notes="Ready.")


def delivery_bundle(status="verified"):
    return build_master_delivery_export_bundle(delivery_index(status=status), bundle_name="Final Package")


def test_builds_workspace_from_v7514_bundle():
    workspace = build_final_delivery_workspace_from_bundle(delivery_bundle())

    assert workspace["schema"] == "socmint.v10_24.final_delivery_workspace"
    assert workspace["version"] == "v10.24.0"
    assert workspace["delivery_action"] == "deliver_ready"
    assert workspace["verification_status"] == "verified"
    assert workspace["package_ready"] is True
    assert workspace["bundle_name"] == "final-package"
    assert workspace["file_count"] == 5
    assert workspace["manifest_file_count"] == 5


def test_builds_workspace_from_v7513_index():
    workspace = build_final_delivery_workspace_from_index(delivery_index(), bundle_name="From Index")

    assert workspace["delivery_action"] == "deliver_ready"
    assert workspace["bundle_name"] == "from-index"
    assert workspace["package_ready"] is True


def test_operator_action_mapping():
    assert operator_actions_for_delivery("deliver_ready") == ["review_final_package", "export_zip", "record_delivery"]
    assert operator_actions_for_delivery("human_review_required") == [
        "review_findings",
        "resolve_or_acknowledge",
        "regenerate_if_needed",
    ]
    assert operator_actions_for_delivery("regenerate_export") == ["regenerate_v7_5_14_package", "rerun_verification"]


def test_human_review_workspace_actions():
    workspace = build_final_delivery_workspace_from_bundle(delivery_bundle(status="needs_human_review"))

    assert workspace["delivery_action"] == "human_review_required"
    assert workspace["package_ready"] is False
    assert workspace["operator_actions"] == ["review_findings", "resolve_or_acknowledge", "regenerate_if_needed"]


def test_regenerate_workspace_actions():
    workspace = build_final_delivery_workspace_from_bundle(delivery_bundle(status="failed"))

    assert workspace["delivery_action"] == "regenerate_export"
    assert workspace["package_ready"] is False
    assert workspace["operator_actions"] == ["regenerate_v7_5_14_package", "rerun_verification"]


def test_preserves_package_file_inventory():
    workspace = build_final_delivery_workspace_from_bundle(delivery_bundle())

    assert {row["path"] for row in workspace["package_files"]} == REQUIRED_FILES


def test_builds_bundle_from_request_with_bundle_passthrough():
    bundle = delivery_bundle()
    result = build_final_delivery_bundle_from_request({"bundle": bundle})

    assert result == bundle


def test_builds_workspace_from_request_with_index():
    workspace = build_final_delivery_workspace_from_request({"index": delivery_index(), "bundle_name": "Request Index"})

    assert workspace["bundle_name"] == "request-index"
    assert workspace["delivery_action"] == "deliver_ready"


def test_export_zip_from_request_contains_required_files():
    zip_bytes = build_final_delivery_export_zip_from_request({"index": delivery_index()})

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        assert set(archive.namelist()) == REQUIRED_FILES


def test_input_payload_is_not_mutated():
    payload = {"index": delivery_index(), "bundle_name": "Mutation Check"}
    original = deepcopy(payload)

    build_final_delivery_workspace_from_request(payload)

    assert payload == original


def test_no_connector_execution_function_is_called(monkeypatch):
    import socmint.v10_24_final_delivery_workspace as workspace_module

    def explode(*_args, **_kwargs):
        raise AssertionError("connector execution must not happen")

    monkeypatch.setattr(workspace_module, "execute_connector", explode, raising=False)

    workspace = build_final_delivery_workspace_from_request({"index": delivery_index()})

    assert workspace["delivery_action"] == "deliver_ready"
