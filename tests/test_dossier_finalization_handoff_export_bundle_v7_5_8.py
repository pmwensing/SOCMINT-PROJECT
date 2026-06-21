from __future__ import annotations

import io
import json
import zipfile
from copy import deepcopy

from socmint.dossier_finalization_certificate_handoff_index_v7_5_7 import (
    build_handoff_index,
)
from socmint.dossier_finalization_handoff_export_bundle_v7_5_8 import (
    build_handoff_export_bundle,
)
from socmint.dossier_finalization_handoff_export_bundle_v7_5_8 import (
    build_handoff_export_bundle_files,
)
from socmint.dossier_finalization_handoff_export_bundle_v7_5_8 import (
    build_handoff_export_bundle_from_verification_report,
)
from socmint.dossier_finalization_handoff_export_bundle_v7_5_8 import (
    build_handoff_export_zip,
)
from socmint.dossier_finalization_handoff_export_bundle_v7_5_8 import (
    handoff_export_manifest,
)
from socmint.dossier_finalization_handoff_export_bundle_v7_5_8 import (
    safe_handoff_bundle_name,
)

REQUIRED_FILES = {
    "README.md",
    "handoff_index.json",
    "handoff_index.md",
    "handoff_index_summary.json",
    "manifest.json",
}


def verified_report():
    return {
        "schema": "socmint.v7_5_6.dossier_finalization_certificate_bundle_verification",
        "status": "verified",
        "verified": True,
        "failure_count": 0,
        "warning_count": 0,
        "certificate_status": "valid",
        "certificate_valid": True,
        "required_files": ["handoff_index.json", "manifest.json"],
        "present_files": ["handoff_index.json", "manifest.json"],
        "missing_files": [],
        "unexpected_files": [],
        "manifest": {
            "files": [
                {
                    "path": "handoff_index.json",
                    "content_type": "application/json",
                    "size_bytes": 123,
                    "sha256": "a" * 64,
                }
            ]
        },
        "file_results": [
            {"path": "handoff_index.json", "hash_match": True, "size_match": True}
        ],
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
            "certificate_status": "failed",
            "certificate_valid": False,
        }
    )
    report["failures"] = [
        {
            "severity": "fail",
            "code": "sha256_mismatch",
            "path": "certificate.json",
            "detail": "Manifest SHA-256 does not match file bytes.",
            "action": "Regenerate the bundle.",
        }
    ]
    return report


def archive_index():
    return build_handoff_index(
        verified_report(), bundle_name="bundle-a", operator="analyst"
    )


def regenerate_index():
    return build_handoff_index(failed_report(), bundle_name="bundle-b")


def test_builds_bundle_from_archive_ready_v757_index():
    bundle = build_handoff_export_bundle(archive_index(), bundle_name="Handoff Bundle")

    assert (
        bundle["schema"] == "socmint.v7_5_8.dossier_finalization_handoff_export_bundle"
    )
    assert bundle["approved_line"] == "v7.5.8"
    assert bundle["bundle_name"] == "handoff-bundle"
    assert bundle["recommended_action"] == "archive_ready"
    assert bundle["verification_status"] == "verified"
    assert bundle["certificate_status"] == "valid"


def test_builds_bundle_from_regenerate_bundle_v757_index():
    bundle = build_handoff_export_bundle(regenerate_index())

    assert bundle["recommended_action"] == "regenerate_bundle"
    assert bundle["verification_status"] == "failed"
    assert bundle["certificate_status"] == "failed"


def test_builds_bundle_from_v756_verification_report():
    bundle = build_handoff_export_bundle_from_verification_report(
        verified_report(), bundle_name="Report Bundle", operator="operator-a"
    )

    assert bundle["bundle_name"] == "report-bundle"
    assert bundle["index"]["operator"] == "operator-a"
    assert bundle["recommended_action"] == "archive_ready"


def test_produces_exactly_required_files():
    files = build_handoff_export_bundle_files(
        build_handoff_export_bundle(archive_index())
    )

    assert set(files) == REQUIRED_FILES
    assert b"SOCMINT v7.5.8 Handoff Index Export Bundle" in files["README.md"]
    assert (
        b"SOCMINT v7.5.7 Certificate Bundle Handoff Index" in files["handoff_index.md"]
    )


def test_manifest_contains_sha256_and_size_for_every_file():
    files = build_handoff_export_bundle_files(
        build_handoff_export_bundle(archive_index())
    )
    manifest = handoff_export_manifest(files)

    assert (
        manifest["schema"]
        == "socmint.v7_5_8.dossier_finalization_handoff_export_manifest"
    )
    assert manifest["file_count"] == len(files)
    for row in manifest["files"]:
        assert row["path"] in files
        assert row["size_bytes"] == len(files[row["path"]])
        assert len(row["sha256"]) == 64
        assert row["content_type"] in {"application/json", "text/markdown"}


def test_zip_contains_all_required_files():
    zip_bytes = build_handoff_export_zip(build_handoff_export_bundle(archive_index()))

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        assert set(archive.namelist()) == REQUIRED_FILES
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["file_count"] == len(REQUIRED_FILES)


def test_safe_bundle_name_strips_unsafe_path_characters():
    assert (
        safe_handoff_bundle_name("../Bad Handoff/Name!!.zip") == "bad-handoff-name-.zip"
    )
    assert safe_handoff_bundle_name("../../") == "socmint-v7.5.8-handoff-index-export"


def test_input_handoff_index_is_not_mutated():
    index = archive_index()
    original = deepcopy(index)

    build_handoff_export_bundle(index)

    assert index == original


def test_bundle_metadata_references_recommended_action_and_statuses():
    index = archive_index()
    bundle = build_handoff_export_bundle(index)

    assert bundle["recommended_action"] == index["recommended_action"]
    assert bundle["verification_status"] == index["verification_status"]
    assert bundle["certificate_status"] == index["certificate_status"]


def test_manifest_file_count_matches_file_list():
    bundle = build_handoff_export_bundle(archive_index())

    assert bundle["manifest"]["file_count"] == len(bundle["files"])
    assert bundle["manifest"]["files"] == bundle["files"]
