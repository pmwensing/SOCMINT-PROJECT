from __future__ import annotations

import io
import json
import zipfile
from copy import deepcopy

from socmint.dossier_finalization_certificate_bundle_v7_5_5 import build_certificate_bundle
from socmint.dossier_finalization_certificate_bundle_v7_5_5 import build_certificate_bundle_files
from socmint.dossier_finalization_certificate_bundle_v7_5_5 import build_certificate_bundle_from_verification_report
from socmint.dossier_finalization_certificate_bundle_v7_5_5 import build_certificate_bundle_zip
from socmint.dossier_finalization_certificate_bundle_v7_5_5 import certificate_bundle_manifest
from socmint.dossier_finalization_certificate_bundle_v7_5_5 import safe_bundle_name
from socmint.dossier_finalization_certificate_v7_5_4 import build_verification_certificate

REQUIRED_FILES = {
    "README.md",
    "certificate.json",
    "certificate.md",
    "certificate_summary.json",
    "manifest.json",
}


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


def valid_certificate():
    return build_verification_certificate(verified_report(), packet_name="packet-a")


def failed_certificate():
    return build_verification_certificate(failed_report(), packet_name="packet-b")


def test_builds_bundle_from_valid_v754_certificate():
    bundle = build_certificate_bundle(valid_certificate(), bundle_name="Bundle A")

    assert bundle["schema"] == "socmint.v7_5_5.dossier_finalization_certificate_bundle"
    assert bundle["approved_line"] == "v7.5.5"
    assert bundle["bundle_name"] == "bundle-a"
    assert bundle["certificate_status"] == "valid"
    assert bundle["certificate_valid"] is True


def test_builds_bundle_from_failed_v754_certificate():
    bundle = build_certificate_bundle(failed_certificate())

    assert bundle["certificate_status"] == "failed"
    assert bundle["certificate_valid"] is False


def test_builds_bundle_from_verification_report():
    bundle = build_certificate_bundle_from_verification_report(verified_report(), bundle_name="Report Bundle", packet_name="packet-a")

    assert bundle["bundle_name"] == "report-bundle"
    assert bundle["certificate"]["packet_name"] == "packet-a"
    assert bundle["certificate_status"] == "valid"


def test_produces_exactly_required_files():
    files = build_certificate_bundle_files(build_certificate_bundle(valid_certificate()))

    assert set(files) == REQUIRED_FILES
    assert b"SOCMINT v7.5.5 Certificate Bundle Export" in files["README.md"]
    assert b"SOCMINT v7.5.4 Finalization Verification Certificate" in files["certificate.md"]


def test_manifest_contains_sha256_and_size_for_every_file():
    files = build_certificate_bundle_files(build_certificate_bundle(valid_certificate()))
    manifest = certificate_bundle_manifest(files)

    assert manifest["schema"] == "socmint.v7_5_5.dossier_finalization_certificate_bundle_manifest"
    assert manifest["file_count"] == len(files)
    for row in manifest["files"]:
        assert row["path"] in files
        assert row["size_bytes"] == len(files[row["path"]])
        assert len(row["sha256"]) == 64
        assert row["content_type"] in {"application/json", "text/markdown"}


def test_zip_contains_all_required_files():
    zip_bytes = build_certificate_bundle_zip(build_certificate_bundle(valid_certificate()))

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        assert set(archive.namelist()) == REQUIRED_FILES
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["file_count"] == len(REQUIRED_FILES)


def test_safe_bundle_name_strips_unsafe_path_characters():
    assert safe_bundle_name("../Bad Bundle/Name!!.zip") == "bad-bundle-name-.zip"
    assert safe_bundle_name("../../") == "socmint-v7.5.5-certificate-bundle"


def test_input_certificate_is_not_mutated():
    certificate = valid_certificate()
    original = deepcopy(certificate)

    build_certificate_bundle(certificate)

    assert certificate == original


def test_bundle_metadata_references_certificate_status_and_sha256():
    certificate = valid_certificate()
    bundle = build_certificate_bundle(certificate)

    assert bundle["certificate_status"] == certificate["status"]
    assert bundle["certificate_sha256"] == certificate["certificate_sha256"]


def test_manifest_file_count_matches_file_list():
    bundle = build_certificate_bundle(valid_certificate())

    assert bundle["manifest"]["file_count"] == len(bundle["files"])
    assert bundle["manifest"]["files"] == bundle["files"]
