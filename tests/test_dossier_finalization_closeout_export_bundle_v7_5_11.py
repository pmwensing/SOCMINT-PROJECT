from __future__ import annotations

import io
import json
import zipfile
from copy import deepcopy

from socmint.dossier_finalization_closeout_export_bundle_v7_5_11 import (
    build_closeout_export_bundle,
)
from socmint.dossier_finalization_closeout_export_bundle_v7_5_11 import (
    build_closeout_export_bundle_files,
)
from socmint.dossier_finalization_closeout_export_bundle_v7_5_11 import (
    build_closeout_export_bundle_from_verification_report,
)
from socmint.dossier_finalization_closeout_export_bundle_v7_5_11 import (
    build_closeout_export_zip,
)
from socmint.dossier_finalization_closeout_export_bundle_v7_5_11 import (
    closeout_export_manifest,
)
from socmint.dossier_finalization_closeout_export_bundle_v7_5_11 import (
    safe_closeout_bundle_name,
)
from socmint.dossier_finalization_closeout_report_v7_5_10 import build_closeout_report

REQUIRED_FILES = {
    "README.md",
    "closeout_report.json",
    "closeout_report.md",
    "closeout_report_summary.json",
    "manifest.json",
}


def verified_report():
    return {
        "schema": "socmint.v7_5_9.dossier_finalization_handoff_export_verification",
        "status": "verified",
        "verified": True,
        "failure_count": 0,
        "warning_count": 0,
        "recommended_action": "archive_ready",
        "verification_status": "verified",
        "certificate_status": "valid",
        "present_files": ["README.md", "handoff_index.json", "manifest.json"],
        "missing_files": [],
        "unexpected_files": [],
        "failures": [],
        "warnings": [],
        "summary": {"status": "verified", "verified": True},
    }


def failed_report():
    report = verified_report()
    report.update(
        {
            "status": "failed",
            "verified": False,
            "failure_count": 1,
            "recommended_action": "regenerate_bundle",
        }
    )
    report["failures"] = [
        {
            "severity": "fail",
            "code": "sha256_mismatch",
            "path": "handoff_index.json",
            "detail": "Manifest SHA-256 does not match file bytes.",
            "action": "Regenerate the v7.5.8 handoff export bundle.",
        }
    ]
    return report


def closeout_ready_report():
    return build_closeout_report(verified_report(), operator="operator-a")


def regenerate_report():
    return build_closeout_report(failed_report())


def test_builds_bundle_from_closeout_ready_v7510_report():
    bundle = build_closeout_export_bundle(
        closeout_ready_report(), bundle_name="Closeout Bundle"
    )

    assert (
        bundle["schema"]
        == "socmint.v7_5_11.dossier_finalization_closeout_export_bundle"
    )
    assert bundle["approved_line"] == "v7.5.11"
    assert bundle["bundle_name"] == "closeout-bundle"
    assert bundle["closeout_action"] == "closeout_ready"
    assert bundle["verification_status"] == "verified"


def test_builds_bundle_from_regenerate_export_v7510_report():
    bundle = build_closeout_export_bundle(regenerate_report())

    assert bundle["closeout_action"] == "regenerate_export"
    assert bundle["verification_status"] == "failed"


def test_builds_bundle_from_v759_verification_report():
    bundle = build_closeout_export_bundle_from_verification_report(
        verified_report(), bundle_name="Report Bundle", operator="operator-a"
    )

    assert bundle["bundle_name"] == "report-bundle"
    assert bundle["report"]["operator"] == "operator-a"
    assert bundle["closeout_action"] == "closeout_ready"


def test_produces_exactly_required_files():
    files = build_closeout_export_bundle_files(
        build_closeout_export_bundle(closeout_ready_report())
    )

    assert set(files) == REQUIRED_FILES
    assert b"SOCMINT v7.5.11 Closeout Report Export Bundle" in files["README.md"]
    assert (
        b"SOCMINT v7.5.10 Finalization Chain Closeout Report"
        in files["closeout_report.md"]
    )


def test_manifest_contains_sha256_and_size_for_every_file():
    files = build_closeout_export_bundle_files(
        build_closeout_export_bundle(closeout_ready_report())
    )
    manifest = closeout_export_manifest(files)

    assert (
        manifest["schema"]
        == "socmint.v7_5_11.dossier_finalization_closeout_export_manifest"
    )
    assert manifest["file_count"] == len(files)
    for row in manifest["files"]:
        assert row["path"] in files
        assert row["size_bytes"] == len(files[row["path"]])
        assert len(row["sha256"]) == 64
        assert row["content_type"] in {"application/json", "text/markdown"}


def test_zip_contains_all_required_files():
    zip_bytes = build_closeout_export_zip(
        build_closeout_export_bundle(closeout_ready_report())
    )

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        assert set(archive.namelist()) == REQUIRED_FILES
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["file_count"] == len(REQUIRED_FILES)


def test_safe_bundle_name_strips_unsafe_path_characters():
    assert (
        safe_closeout_bundle_name("../Bad Closeout/Name!!.zip")
        == "bad-closeout-name-.zip"
    )
    assert (
        safe_closeout_bundle_name("../../") == "socmint-v7.5.11-closeout-report-export"
    )


def test_input_closeout_report_is_not_mutated():
    report = closeout_ready_report()
    original = deepcopy(report)

    build_closeout_export_bundle(report)

    assert report == original


def test_bundle_metadata_references_closeout_action_and_verification_status():
    report = closeout_ready_report()
    bundle = build_closeout_export_bundle(report)

    assert bundle["closeout_action"] == report["closeout_action"]
    assert bundle["verification_status"] == report["verification_status"]


def test_manifest_file_count_matches_file_list():
    bundle = build_closeout_export_bundle(closeout_ready_report())

    assert bundle["manifest"]["file_count"] == len(bundle["files"])
    assert bundle["manifest"]["files"] == bundle["files"]
