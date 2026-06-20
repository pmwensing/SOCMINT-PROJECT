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
    build_handoff_export_zip,
)
from socmint.dossier_finalization_handoff_export_bundle_v7_5_8 import canonical_json
from socmint.dossier_finalization_handoff_export_verify_v7_5_9 import (
    summarize_handoff_export_verification,
)
from socmint.dossier_finalization_handoff_export_verify_v7_5_9 import (
    verify_handoff_export_bundle,
)
from socmint.dossier_finalization_handoff_export_verify_v7_5_9 import (
    verify_handoff_export_files,
)
from socmint.dossier_finalization_handoff_export_verify_v7_5_9 import (
    verify_handoff_export_zip,
)


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


def archive_bundle():
    index = build_handoff_index(
        verified_report(), bundle_name="bundle-a", operator="analyst"
    )
    return build_handoff_export_bundle(index, bundle_name="handoff-export")


def regenerate_bundle():
    index = build_handoff_index(failed_report(), bundle_name="bundle-b")
    return build_handoff_export_bundle(index, bundle_name="regenerate-export")


def archive_files():
    return build_handoff_export_bundle_files(archive_bundle())


def test_verifies_archive_ready_v758_bundle_as_verified():
    report = verify_handoff_export_bundle(archive_bundle())

    assert (
        report["schema"]
        == "socmint.v7_5_9.dossier_finalization_handoff_export_verification"
    )
    assert report["status"] == "verified"
    assert report["verified"] is True
    assert report["failure_count"] == 0
    assert report["warning_count"] == 0


def test_verifies_v758_zip_bytes_as_verified():
    report = verify_handoff_export_zip(build_handoff_export_zip(archive_bundle()))

    assert report["status"] == "verified"
    assert report["verified"] is True


def test_fails_when_manifest_json_is_missing():
    files = archive_files()
    files.pop("manifest.json")

    report = verify_handoff_export_files(files)

    assert report["status"] == "failed"
    assert any(
        item["code"] == "missing_required_file" and item["path"] == "manifest.json"
        for item in report["failures"]
    )


def test_fails_when_required_file_is_missing():
    files = archive_files()
    files.pop("README.md")

    report = verify_handoff_export_files(files)

    assert report["status"] == "failed"
    assert any(
        item["code"] == "missing_required_file" and item["path"] == "README.md"
        for item in report["failures"]
    )


def test_fails_when_sha256_does_not_match():
    files = archive_files()
    files["handoff_index.json"] = b"tampered\n"

    report = verify_handoff_export_files(files)

    assert report["status"] == "failed"
    assert any(
        item["code"] == "sha256_mismatch" and item["path"] == "handoff_index.json"
        for item in report["failures"]
    )


def test_fails_when_size_does_not_match():
    files = archive_files()
    manifest = json.loads(files["manifest.json"])
    for row in manifest["files"]:
        if row["path"] == "handoff_index.json":
            row["size_bytes"] += 1
    files["manifest.json"] = canonical_json(manifest).encode("utf-8")

    report = verify_handoff_export_files(files)

    assert report["status"] == "failed"
    assert any(
        item["code"] == "size_mismatch" and item["path"] == "handoff_index.json"
        for item in report["failures"]
    )


def test_fails_when_handoff_summary_recommended_action_differs():
    files = archive_files()
    summary = json.loads(files["handoff_index_summary.json"])
    summary["recommended_action"] = "regenerate_bundle"
    files["handoff_index_summary.json"] = canonical_json(summary).encode("utf-8")
    manifest = json.loads(files["manifest.json"])
    for row in manifest["files"]:
        if row["path"] == "handoff_index_summary.json":
            import hashlib

            row["sha256"] = hashlib.sha256(
                files["handoff_index_summary.json"]
            ).hexdigest()
            row["size_bytes"] = len(files["handoff_index_summary.json"])
    files["manifest.json"] = canonical_json(manifest).encode("utf-8")

    report = verify_handoff_export_files(files)

    assert report["status"] == "failed"
    assert any(
        item["code"] == "recommended_action_mismatch" for item in report["failures"]
    )


def test_needs_human_review_when_unexpected_extra_file_exists():
    files = archive_files()
    files["extra.txt"] = b"extra\n"
    manifest = json.loads(files["manifest.json"])
    import hashlib

    manifest["files"].append(
        {
            "path": "extra.txt",
            "content_type": "text/plain",
            "size_bytes": len(files["extra.txt"]),
            "sha256": hashlib.sha256(files["extra.txt"]).hexdigest(),
        }
    )
    manifest["file_count"] = len(files)
    files["manifest.json"] = canonical_json(manifest).encode("utf-8")

    report = verify_handoff_export_files(files)

    assert report["status"] == "needs_human_review"
    assert any(item["code"] == "unexpected_file" for item in report["warnings"])


def test_needs_human_review_when_recommended_action_is_regenerate_but_hashes_match():
    report = verify_handoff_export_bundle(regenerate_bundle())

    assert report["status"] == "needs_human_review"
    assert any(
        item["code"] == "non_archive_ready_handoff" for item in report["warnings"]
    )


def test_fails_on_path_traversal_zip_entry():
    files = archive_files()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for path, data in files.items():
            archive.writestr(path, data)
        archive.writestr("../evil.txt", b"nope")

    report = verify_handoff_export_zip(buffer.getvalue())

    assert report["status"] == "failed"
    assert any(item["code"] == "unsafe_zip_path" for item in report["failures"])


def test_summary_is_compact():
    report = verify_handoff_export_bundle(archive_bundle())
    summary = summarize_handoff_export_verification(report)

    assert (
        summary["schema"]
        == "socmint.v7_5_9.dossier_finalization_handoff_export_verification.summary"
    )
    assert summary["status"] == "verified"
    assert summary["verified"] is True
    assert "manifest" not in summary
    assert "file_results" not in summary


def test_input_file_map_is_not_mutated():
    files = archive_files()
    original = deepcopy(files)

    verify_handoff_export_files(files)

    assert files == original
