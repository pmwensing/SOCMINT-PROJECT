from __future__ import annotations

from copy import deepcopy

from socmint.dossier_finalization_certificate_handoff_index_v7_5_7 import build_handoff_index
from socmint.dossier_finalization_closeout_report_v7_5_10 import ACTION_CLOSEOUT
from socmint.dossier_finalization_closeout_report_v7_5_10 import ACTION_REGENERATE
from socmint.dossier_finalization_closeout_report_v7_5_10 import ACTION_REVIEW
from socmint.dossier_finalization_closeout_report_v7_5_10 import build_closeout_report
from socmint.dossier_finalization_closeout_report_v7_5_10 import build_closeout_report_from_bundle
from socmint.dossier_finalization_closeout_report_v7_5_10 import build_closeout_report_from_zip_bytes
from socmint.dossier_finalization_closeout_report_v7_5_10 import recommended_closeout_action
from socmint.dossier_finalization_closeout_report_v7_5_10 import render_closeout_report_markdown
from socmint.dossier_finalization_closeout_report_v7_5_10 import summarize_closeout_report
from socmint.dossier_finalization_handoff_export_bundle_v7_5_8 import build_handoff_export_bundle
from socmint.dossier_finalization_handoff_export_bundle_v7_5_8 import build_handoff_export_zip


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


def review_report():
    report = verified_report()
    report.update({"status": "needs_human_review", "verified": False, "warning_count": 1, "recommended_action": "human_review_required"})
    report["warnings"] = [
        {
            "severity": "warn",
            "code": "non_archive_ready_handoff",
            "path": "handoff_index.json",
            "detail": "Handoff export is structurally intact but not archive-ready.",
            "action": "Complete human review or regenerate the bundle before handoff.",
        }
    ]
    return report


def failed_report():
    report = verified_report()
    report.update({"status": "failed", "verified": False, "failure_count": 1, "recommended_action": "regenerate_bundle"})
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


def v756_report():
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
        "manifest": {"files": [{"path": "handoff_index.json", "content_type": "application/json", "size_bytes": 123, "sha256": "a" * 64}]},
        "file_results": [{"path": "handoff_index.json", "hash_match": True, "size_match": True}],
        "failures": [],
        "warnings": [],
        "summary": {"status": "verified", "verified": True},
    }


def handoff_export_bundle():
    index = build_handoff_index(v756_report(), bundle_name="bundle-a", operator="analyst")
    return build_handoff_export_bundle(index, bundle_name="closeout-source")


def test_builds_closeout_ready_report_from_verified_archive_ready_report():
    report = build_closeout_report(verified_report(), operator="operator-a")

    assert report["schema"] == "socmint.v7_5_10.dossier_finalization_closeout_report"
    assert report["closeout_action"] == ACTION_CLOSEOUT
    assert report["verified"] is True
    assert report["operator"] == "operator-a"


def test_builds_human_review_report_from_needs_review_report():
    report = build_closeout_report(review_report())

    assert report["closeout_action"] == ACTION_REVIEW
    assert report["warning_count"] == 1
    assert report["findings"][0]["code"] == "non_archive_ready_handoff"


def test_builds_regenerate_export_report_from_failed_report():
    report = build_closeout_report(failed_report())

    assert report["closeout_action"] == ACTION_REGENERATE
    assert report["failure_count"] == 1
    assert report["findings"][0]["code"] == "sha256_mismatch"


def test_builds_report_from_v758_handoff_export_bundle():
    report = build_closeout_report_from_bundle(handoff_export_bundle(), operator="operator-a")

    assert report["closeout_action"] == ACTION_CLOSEOUT
    assert report["operator"] == "operator-a"
    assert report["file_count"] >= 5


def test_builds_report_from_v758_zip_bytes():
    zip_bytes = build_handoff_export_zip(handoff_export_bundle())
    report = build_closeout_report_from_zip_bytes(zip_bytes)

    assert report["closeout_action"] == ACTION_CLOSEOUT
    assert report["verification_status"] == "verified"


def test_findings_combine_failures_and_warnings():
    source = failed_report()
    source["warnings"] = review_report()["warnings"]
    report = build_closeout_report(source)

    assert [item["code"] for item in report["findings"]] == ["sha256_mismatch", "non_archive_ready_handoff"]


def test_summary_is_compact_and_excludes_full_findings():
    report = build_closeout_report(verified_report())
    summary = summarize_closeout_report(report)

    assert summary["schema"] == "socmint.v7_5_10.dossier_finalization_closeout_report.summary"
    assert summary["closeout_action"] == ACTION_CLOSEOUT
    assert "findings" not in summary


def test_markdown_includes_required_headings():
    markdown = render_closeout_report_markdown(build_closeout_report(verified_report()))

    assert "# SOCMINT v7.5.10 Finalization Chain Closeout Report" in markdown
    assert "Closeout action: CLOSEOUT READY" in markdown
    assert "## Chain Status" in markdown
    assert "## Verification" in markdown
    assert "## Findings" in markdown
    assert "## Operator Notes" in markdown


def test_markdown_prints_none_for_empty_findings():
    markdown = render_closeout_report_markdown(build_closeout_report(verified_report()))

    assert "None." in markdown


def test_closeout_action_handles_unknown_status_as_regenerate_export():
    assert recommended_closeout_action({"status": "mystery", "recommended_action": "archive_ready"}) == ACTION_REGENERATE


def test_input_verification_report_is_not_mutated():
    source = review_report()
    original = deepcopy(source)

    build_closeout_report(source)

    assert source == original


def test_file_missing_unexpected_counts_are_preserved():
    source = verified_report()
    source["missing_files"] = ["manifest.json"]
    source["unexpected_files"] = ["extra.txt"]
    source["present_files"] = ["README.md"]
    report = build_closeout_report(source)

    assert report["file_count"] == 1
    assert report["missing_files"] == ["manifest.json"]
    assert report["unexpected_files"] == ["extra.txt"]
