from __future__ import annotations

from copy import deepcopy

from socmint.dossier_finalization_certificate_bundle_v7_5_5 import build_certificate_bundle
from socmint.dossier_finalization_certificate_bundle_v7_5_5 import build_certificate_bundle_zip
from socmint.dossier_finalization_certificate_bundle_verify_v7_5_6 import verify_certificate_bundle
from socmint.dossier_finalization_certificate_handoff_index_v7_5_7 import ACTION_ARCHIVE
from socmint.dossier_finalization_certificate_handoff_index_v7_5_7 import ACTION_REGENERATE
from socmint.dossier_finalization_certificate_handoff_index_v7_5_7 import ACTION_REVIEW
from socmint.dossier_finalization_certificate_handoff_index_v7_5_7 import build_handoff_index
from socmint.dossier_finalization_certificate_handoff_index_v7_5_7 import build_handoff_index_from_bundle
from socmint.dossier_finalization_certificate_handoff_index_v7_5_7 import build_handoff_index_from_zip_bytes
from socmint.dossier_finalization_certificate_handoff_index_v7_5_7 import recommended_action
from socmint.dossier_finalization_certificate_handoff_index_v7_5_7 import render_handoff_index_markdown
from socmint.dossier_finalization_certificate_handoff_index_v7_5_7 import summarize_handoff_index
from socmint.dossier_finalization_certificate_v7_5_4 import build_verification_certificate


def verified_report():
    return {
        "schema": "socmint.v7_5_6.dossier_finalization_certificate_bundle_verification",
        "status": "verified",
        "verified": True,
        "failure_count": 0,
        "warning_count": 0,
        "certificate_status": "valid",
        "certificate_valid": True,
        "required_files": ["certificate.json", "manifest.json"],
        "present_files": ["certificate.json", "manifest.json"],
        "missing_files": [],
        "unexpected_files": [],
        "manifest": {
            "files": [
                {
                    "path": "certificate.json",
                    "content_type": "application/json",
                    "size_bytes": 123,
                    "sha256": "a" * 64,
                }
            ]
        },
        "file_results": [{"path": "certificate.json", "hash_match": True, "size_match": True}],
        "failures": [],
        "warnings": [],
        "summary": {"status": "verified", "verified": True},
    }


def review_report():
    report = verified_report()
    report.update({"status": "needs_human_review", "verified": False, "warning_count": 1, "certificate_status": "needs_human_review", "certificate_valid": False})
    report["warnings"] = [
        {
            "severity": "warn",
            "code": "non_valid_certificate",
            "path": "certificate.json",
            "detail": "Certificate is structurally intact but not valid.",
            "action": "Complete human review before handoff.",
        }
    ]
    return report


def failed_report():
    report = verified_report()
    report.update({"status": "failed", "verified": False, "failure_count": 1, "certificate_status": "failed", "certificate_valid": False})
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


def base_v753_report():
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


def valid_bundle():
    certificate = build_verification_certificate(base_v753_report(), packet_name="packet-a")
    return build_certificate_bundle(certificate, bundle_name="bundle-a")


def test_builds_archive_ready_index_from_verified_report():
    index = build_handoff_index(verified_report(), bundle_name="bundle-a", operator="analyst")

    assert index["schema"] == "socmint.v7_5_7.dossier_finalization_certificate_handoff_index"
    assert index["recommended_action"] == ACTION_ARCHIVE
    assert index["verified"] is True
    assert index["certificate_status"] == "valid"
    assert index["operator"] == "analyst"


def test_builds_human_review_index_from_review_report():
    index = build_handoff_index(review_report())

    assert index["recommended_action"] == ACTION_REVIEW
    assert index["findings"][0]["code"] == "non_valid_certificate"


def test_builds_regenerate_bundle_index_from_failed_report():
    index = build_handoff_index(failed_report())

    assert index["recommended_action"] == ACTION_REGENERATE
    assert index["findings"][0]["code"] == "sha256_mismatch"


def test_builds_index_from_v755_bundle():
    index = build_handoff_index_from_bundle(valid_bundle(), operator="operator-a")

    assert index["recommended_action"] == ACTION_ARCHIVE
    assert index["bundle_name"] == "bundle-a"
    assert index["operator"] == "operator-a"


def test_builds_index_from_v755_zip_bytes():
    zip_bytes = build_certificate_bundle_zip(valid_bundle())
    index = build_handoff_index_from_zip_bytes(zip_bytes, bundle_name="zip-bundle")

    assert index["recommended_action"] == ACTION_ARCHIVE
    assert index["bundle_name"] == "zip-bundle"


def test_file_index_derives_from_manifest_rows():
    index = build_handoff_index(verified_report())

    assert index["file_index"]
    assert index["file_index"][0]["path"] == "certificate.json"
    assert index["file_index"][0]["verified"] is True


def test_findings_combine_failures_and_warnings():
    report = failed_report()
    report["warnings"] = review_report()["warnings"]
    index = build_handoff_index(report)

    codes = [item["code"] for item in index["findings"]]
    assert codes == ["sha256_mismatch", "non_valid_certificate"]


def test_summary_is_compact_and_excludes_full_file_index_and_findings():
    index = build_handoff_index(verified_report(), bundle_name="bundle-a")
    summary = summarize_handoff_index(index)

    assert summary["schema"] == "socmint.v7_5_7.dossier_finalization_certificate_handoff_index.summary"
    assert summary["recommended_action"] == ACTION_ARCHIVE
    assert summary["bundle_name"] == "bundle-a"
    assert "file_index" not in summary
    assert "findings" not in summary


def test_markdown_includes_required_headings():
    markdown = render_handoff_index_markdown(build_handoff_index(verified_report()))

    assert "# SOCMINT v7.5.7 Certificate Bundle Handoff Index" in markdown
    assert "Recommended action: ARCHIVE READY" in markdown
    assert "## Bundle" in markdown
    assert "## Verification" in markdown
    assert "## File Index" in markdown
    assert "## Findings" in markdown
    assert "## Notes" in markdown


def test_markdown_prints_none_for_empty_findings():
    markdown = render_handoff_index_markdown(build_handoff_index(verified_report()))

    assert "None." in markdown


def test_recommended_action_handles_unknown_status_as_regenerate():
    assert recommended_action({"status": "mystery", "certificate_status": "valid"}) == ACTION_REGENERATE


def test_input_verification_report_is_not_mutated():
    report = review_report()
    original = deepcopy(report)

    build_handoff_index(report)

    assert report == original


def test_build_from_bundle_uses_v756_verifier():
    report = verify_certificate_bundle(valid_bundle())
    assert report["status"] == "verified"
