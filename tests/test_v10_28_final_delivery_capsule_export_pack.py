from __future__ import annotations

import io
import zipfile
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
from socmint.v10_28_final_delivery_capsule_export_pack import (
    build_final_delivery_capsule_export_pack_files,
)
from socmint.v10_28_final_delivery_capsule_export_pack import (
    build_final_delivery_capsule_export_pack_from_request,
)
from socmint.v10_28_final_delivery_capsule_export_pack import (
    build_final_delivery_capsule_export_zip,
)
from socmint.v10_28_final_delivery_capsule_export_pack import sha256_bytes

REQUIRED_FILES = {
    "README.md",
    "final_delivery_evidence_capsule.json",
    "final_delivery_evidence_capsule_summary.json",
    "operator_receipt.json",
    "manifest.json",
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
        "closeout_action": "closeout_ready"
        if status == "verified"
        else "regenerate_export",
        "verification_status": status,
        "failures": [
            {
                "severity": "fail",
                "code": "failed_export",
                "path": "final_delivery_evidence_capsule.json",
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
                "path": "final_delivery_evidence_capsule.json",
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


def capsule(status="verified"):
    bundle = build_master_delivery_export_bundle(
        delivery_index(status), bundle_name="Export Pack"
    )
    workspace = build_final_delivery_workspace_from_bundle(bundle)
    console = build_operator_console_from_workspace(workspace)
    audit_trail = build_final_delivery_audit_trail_from_console(console)
    return build_final_delivery_evidence_capsule_from_audit_trail(audit_trail)


def test_builds_export_pack_from_ready_capsule():
    pack = build_final_delivery_capsule_export_pack(capsule())

    assert pack["schema"] == "socmint.v10_28.final_delivery_capsule_export_pack"
    assert pack["version"] == "v10.28.0"
    assert pack["capsule_id"] == pack["capsule"]["capsule_id"]
    assert pack["readiness"] == "ready"
    assert pack["bundle_name"] == "export-pack"
    assert pack["file_count"] == 5
    assert pack["pack_id"]


def test_builds_export_pack_from_review_required_capsule():
    pack = build_final_delivery_capsule_export_pack(capsule("needs_human_review"))

    assert pack["readiness"] == "review_required"
    assert pack["capsule"]["operator_receipt"]["export_available"] is False


def test_builds_export_pack_from_blocked_capsule():
    pack = build_final_delivery_capsule_export_pack(capsule("failed"))

    assert pack["readiness"] == "blocked"
    assert pack["capsule"]["operator_receipt"]["export_available"] is False


def test_required_files_are_present_exactly():
    pack = build_final_delivery_capsule_export_pack(capsule())
    files = build_final_delivery_capsule_export_pack_files(pack)

    assert set(files) == REQUIRED_FILES


def test_manifest_hashes_and_sizes_match_payload_files():
    pack = build_final_delivery_capsule_export_pack(capsule())
    files = build_final_delivery_capsule_export_pack_files(pack)

    for row in pack["manifest"]["files"]:
        path = row["path"]
        if path == "manifest.json":
            continue
        assert row["size_bytes"] == len(files[path])
        assert row["sha256"] == sha256_bytes(files[path])


def test_manifest_uses_self_reference_for_manifest_json():
    pack = build_final_delivery_capsule_export_pack(capsule())
    row = next(
        item for item in pack["manifest"]["files"] if item["path"] == "manifest.json"
    )

    assert row["self_reference"] is True
    assert row["size_bytes"] == 0
    assert row["sha256"] == ""


def test_zip_contains_required_files_exactly():
    pack = build_final_delivery_capsule_export_pack(capsule())
    zip_bytes = build_final_delivery_capsule_export_zip(pack)

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        assert set(archive.namelist()) == REQUIRED_FILES


def test_builds_export_pack_from_request_capsule_shape():
    source = capsule()
    pack = build_final_delivery_capsule_export_pack_from_request({"capsule": source})

    assert pack["capsule_id"] == source["capsule_id"]
    assert pack["readiness"] == "ready"


def test_builds_export_pack_from_request_index_shape():
    pack = build_final_delivery_capsule_export_pack_from_request(
        {"index": delivery_index(), "bundle_name": "Index Export"}
    )

    assert pack["readiness"] == "ready"
    assert pack["bundle_name"] == "index-export"


def test_input_capsule_is_not_mutated():
    source = capsule()
    original = deepcopy(source)

    build_final_delivery_capsule_export_pack(source)

    assert source == original


def test_no_connector_execution_function_is_called(monkeypatch):
    import socmint.v10_28_final_delivery_capsule_export_pack as pack_module

    def explode(*_args, **_kwargs):
        raise AssertionError("connector execution must not happen")

    monkeypatch.setattr(pack_module, "execute_connector", explode, raising=False)

    pack = build_final_delivery_capsule_export_pack_from_request(
        {"index": delivery_index()}
    )

    assert pack["readiness"] == "ready"
