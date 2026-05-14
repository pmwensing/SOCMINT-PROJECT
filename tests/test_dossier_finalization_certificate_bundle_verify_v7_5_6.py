from __future__ import annotations

import io
import json
import zipfile
from copy import deepcopy

from socmint.dossier_finalization_certificate_bundle_v7_5_5 import build_certificate_bundle
from socmint.dossier_finalization_certificate_bundle_v7_5_5 import build_certificate_bundle_files
from socmint.dossier_finalization_certificate_bundle_v7_5_5 import build_certificate_bundle_zip
from socmint.dossier_finalization_certificate_bundle_v7_5_5 import canonical_json
from socmint.dossier_finalization_certificate_v7_5_4 import build_verification_certificate
from socmint.dossier_finalization_certificate_bundle_verify_v7_5_6 import summarize_bundle_verification
from socmint.dossier_finalization_certificate_bundle_verify_v7_5_6 import verify_certificate_bundle
from socmint.dossier_finalization_certificate_bundle_verify_v7_5_6 import verify_certificate_bundle_files
from socmint.dossier_finalization_certificate_bundle_verify_v7_5_6 import verify_certificate_bundle_zip


def verified_report():
    return {
        "schema": "socmint.v7_5_3.dossier_finalization_export_verification",
        "status": "verified",
        "verified": True,
        "failure_count": 0,
        "warning_count": 0,
        "required_files": ["manifest.json"],
        "present_files": ["manifest.json"],
        "missing_files": [],
        "unexpected_files": [],
        "failures": [],
        "warnings": [],
        "summary": {"status": "verified", "verified": True},
    }


def failed_report():
    report = verified_report()
    report.update({"status": "failed", "verified": False, "failure_count": 1})
    report["failures"] = [
        {
            "severity": "fail",
            "code": "sha256_mismatch",
            "path": "README.md",
            "detail": "Manifest SHA-256 does not match file bytes.",
            "action": "Do not archive or disclose this packet; regenerate the export.",
        }
    ]
    return report


def valid_bundle():
    return build_certificate_bundle(build_verification_certificate(verified_report(), packet_name="packet-a"))


def failed_bundle():
    return build_certificate_bundle(build_verification_certificate(failed_report(), packet_name="packet-b"))


def valid_files():
    return build_certificate_bundle_files(valid_bundle())


def test_verifies_valid_v755_bundle_as_verified():
    report = verify_certificate_bundle(valid_bundle())

    assert report["schema"] == "socmint.v7_5_6.dossier_finalization_certificate_bundle_verification"
    assert report["status"] == "verified"
    assert report["verified"] is True
    assert report["failure_count"] == 0
    assert report["warning_count"] == 0


def test_verifies_v755_zip_bytes_as_verified():
    report = verify_certificate_bundle_zip(build_certificate_bundle_zip(valid_bundle()))

    assert report["status"] == "verified"
    assert report["verified"] is True


def test_fails_when_manifest_json_is_missing():
    files = valid_files()
    files.pop("manifest.json")

    report = verify_certificate_bundle_files(files)

    assert report["status"] == "failed"
    assert any(item["code"] == "missing_required_file" and item["path"] == "manifest.json" for item in report["failures"])


def test_fails_when_required_file_is_missing():
    files = valid_files()
    files.pop("README.md")

    report = verify_certificate_bundle_files(files)

    assert report["status"] == "failed"
    assert any(item["code"] == "missing_required_file" and item["path"] == "README.md" for item in report["failures"])


def test_fails_when_sha256_does_not_match():
    files = valid_files()
    files["certificate.json"] = b"tampered\n"

    report = verify_certificate_bundle_files(files)

    assert report["status"] == "failed"
    assert any(item["code"] == "sha256_mismatch" and item["path"] == "certificate.json" for item in report["failures"])


def test_fails_when_size_does_not_match():
    files = valid_files()
    manifest = json.loads(files["manifest.json"])
    for row in manifest["files"]:
        if row["path"] == "certificate.json":
            row["size_bytes"] += 1
    files["manifest.json"] = canonical_json(manifest).encode("utf-8")

    report = verify_certificate_bundle_files(files)

    assert report["status"] == "failed"
    assert any(item["code"] == "size_mismatch" and item["path"] == "certificate.json" for item in report["failures"])


def test_fails_when_certificate_summary_status_differs():
    files = valid_files()
    summary = json.loads(files["certificate_summary.json"])
    summary["status"] = "failed"
    files["certificate_summary.json"] = canonical_json(summary).encode("utf-8")
    manifest = json.loads(files["manifest.json"])
    for row in manifest["files"]:
        if row["path"] == "certificate_summary.json":
            import hashlib

            row["sha256"] = hashlib.sha256(files["certificate_summary.json"]).hexdigest()
            row["size_bytes"] = len(files["certificate_summary.json"])
    files["manifest.json"] = canonical_json(manifest).encode("utf-8")

    report = verify_certificate_bundle_files(files)

    assert report["status"] == "failed"
    assert any(item["code"] == "certificate_status_mismatch" for item in report["failures"])


def test_fails_when_certificate_digest_is_wrong():
    files = valid_files()
    certificate = json.loads(files["certificate.json"])
    certificate["certificate_sha256"] = "0" * 64
    files["certificate.json"] = canonical_json(certificate).encode("utf-8")
    manifest = json.loads(files["manifest.json"])
    for row in manifest["files"]:
        if row["path"] == "certificate.json":
            import hashlib

            row["sha256"] = hashlib.sha256(files["certificate.json"]).hexdigest()
            row["size_bytes"] = len(files["certificate.json"])
    files["manifest.json"] = canonical_json(manifest).encode("utf-8")

    report = verify_certificate_bundle_files(files)

    assert report["status"] == "failed"
    assert any(item["code"] == "certificate_digest_mismatch" for item in report["failures"])


def test_needs_human_review_when_unexpected_extra_file_exists():
    files = valid_files()
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

    report = verify_certificate_bundle_files(files)

    assert report["status"] == "needs_human_review"
    assert any(item["code"] == "unexpected_file" for item in report["warnings"])


def test_needs_human_review_when_certificate_status_is_failed_but_hashes_match():
    report = verify_certificate_bundle(failed_bundle())

    assert report["status"] == "needs_human_review"
    assert any(item["code"] == "non_valid_certificate" for item in report["warnings"])


def test_fails_on_path_traversal_zip_entry():
    files = valid_files()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for path, data in files.items():
            archive.writestr(path, data)
        archive.writestr("../evil.txt", b"nope")

    report = verify_certificate_bundle_zip(buffer.getvalue())

    assert report["status"] == "failed"
    assert any(item["code"] == "unsafe_zip_path" for item in report["failures"])


def test_summary_is_compact():
    report = verify_certificate_bundle(valid_bundle())
    summary = summarize_bundle_verification(report)

    assert summary["schema"] == "socmint.v7_5_6.dossier_finalization_certificate_bundle_verification.summary"
    assert summary["status"] == "verified"
    assert summary["verified"] is True
    assert "manifest" not in summary
    assert "file_results" not in summary


def test_input_file_map_is_not_mutated():
    files = valid_files()
    original = deepcopy(files)

    verify_certificate_bundle_files(files)

    assert files == original
