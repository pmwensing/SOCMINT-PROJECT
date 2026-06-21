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
    build_closeout_export_zip,
)
from socmint.dossier_finalization_closeout_export_bundle_v7_5_11 import canonical_json
from socmint.dossier_finalization_closeout_report_v7_5_10 import build_closeout_report
from socmint.dossier_finalization_closeout_export_verify_v7_5_12 import (
    summarize_closeout_export_verification,
)
from socmint.dossier_finalization_closeout_export_verify_v7_5_12 import (
    verify_closeout_export_bundle,
)
from socmint.dossier_finalization_closeout_export_verify_v7_5_12 import (
    verify_closeout_export_files,
)
from socmint.dossier_finalization_closeout_export_verify_v7_5_12 import (
    verify_closeout_export_zip,
)


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


def closeout_bundle():
    closeout_report = build_closeout_report(verified_report(), operator="operator-a")
    return build_closeout_export_bundle(closeout_report, bundle_name="closeout-export")


def regenerate_bundle():
    closeout_report = build_closeout_report(failed_report())
    return build_closeout_export_bundle(
        closeout_report, bundle_name="regenerate-export"
    )


def closeout_files():
    return build_closeout_export_bundle_files(closeout_bundle())


def test_verifies_closeout_ready_v7511_bundle_as_verified():
    report = verify_closeout_export_bundle(closeout_bundle())

    assert (
        report["schema"]
        == "socmint.v7_5_12.dossier_finalization_closeout_export_verification"
    )
    assert report["status"] == "verified"
    assert report["verified"] is True
    assert report["failure_count"] == 0
    assert report["warning_count"] == 0


def test_verifies_v7511_zip_bytes_as_verified():
    report = verify_closeout_export_zip(build_closeout_export_zip(closeout_bundle()))

    assert report["status"] == "verified"
    assert report["verified"] is True


def test_fails_when_manifest_json_is_missing():
    files = closeout_files()
    files.pop("manifest.json")

    report = verify_closeout_export_files(files)

    assert report["status"] == "failed"
    assert any(
        item["code"] == "missing_required_file" and item["path"] == "manifest.json"
        for item in report["failures"]
    )


def test_fails_when_required_file_is_missing():
    files = closeout_files()
    files.pop("README.md")

    report = verify_closeout_export_files(files)

    assert report["status"] == "failed"
    assert any(
        item["code"] == "missing_required_file" and item["path"] == "README.md"
        for item in report["failures"]
    )


def test_fails_when_sha256_does_not_match():
    files = closeout_files()
    files["closeout_report.json"] = b"tampered\n"

    report = verify_closeout_export_files(files)

    assert report["status"] == "failed"
    assert any(
        item["code"] == "sha256_mismatch" and item["path"] == "closeout_report.json"
        for item in report["failures"]
    )


def test_fails_when_size_does_not_match():
    files = closeout_files()
    manifest = json.loads(files["manifest.json"])
    for row in manifest["files"]:
        if row["path"] == "closeout_report.json":
            row["size_bytes"] += 1
    files["manifest.json"] = canonical_json(manifest).encode("utf-8")

    report = verify_closeout_export_files(files)

    assert report["status"] == "failed"
    assert any(
        item["code"] == "size_mismatch" and item["path"] == "closeout_report.json"
        for item in report["failures"]
    )


def test_fails_when_closeout_summary_action_differs():
    files = closeout_files()
    summary = json.loads(files["closeout_report_summary.json"])
    summary["closeout_action"] = "regenerate_export"
    files["closeout_report_summary.json"] = canonical_json(summary).encode("utf-8")
    manifest = json.loads(files["manifest.json"])
    for row in manifest["files"]:
        if row["path"] == "closeout_report_summary.json":
            import hashlib

            row["sha256"] = hashlib.sha256(
                files["closeout_report_summary.json"]
            ).hexdigest()
            row["size_bytes"] = len(files["closeout_report_summary.json"])
    files["manifest.json"] = canonical_json(manifest).encode("utf-8")

    report = verify_closeout_export_files(files)

    assert report["status"] == "failed"
    assert any(
        item["code"] == "closeout_action_mismatch" for item in report["failures"]
    )


def test_needs_human_review_when_unexpected_extra_file_exists():
    files = closeout_files()
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

    report = verify_closeout_export_files(files)

    assert report["status"] == "needs_human_review"
    assert any(item["code"] == "unexpected_file" for item in report["warnings"])


def test_needs_human_review_when_closeout_action_is_regenerate_but_hashes_match():
    report = verify_closeout_export_bundle(regenerate_bundle())

    assert report["status"] == "needs_human_review"
    assert any(item["code"] == "non_closeout_ready" for item in report["warnings"])


def test_fails_on_path_traversal_zip_entry():
    files = closeout_files()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for path, data in files.items():
            archive.writestr(path, data)
        archive.writestr("../extra.txt", b"nope")

    report = verify_closeout_export_zip(buffer.getvalue())

    assert report["status"] == "failed"
    assert any(item["code"] == "unsafe_zip_path" for item in report["failures"])


def test_summary_is_compact():
    report = verify_closeout_export_bundle(closeout_bundle())
    summary = summarize_closeout_export_verification(report)

    assert (
        summary["schema"]
        == "socmint.v7_5_12.dossier_finalization_closeout_export_verification.summary"
    )
    assert summary["status"] == "verified"
    assert summary["verified"] is True
    assert "manifest" not in summary
    assert "file_results" not in summary


def test_input_file_map_is_not_mutated():
    files = closeout_files()
    original = deepcopy(files)

    verify_closeout_export_files(files)

    assert files == original
