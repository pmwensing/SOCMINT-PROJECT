from __future__ import annotations

from copy import deepcopy

from socmint.dossier_finalization_closeout_export_bundle_v7_5_11 import (
    build_closeout_export_bundle,
)
from socmint.dossier_finalization_closeout_export_bundle_v7_5_11 import (
    build_closeout_export_zip,
)
from socmint.dossier_finalization_closeout_report_v7_5_10 import build_closeout_report
from socmint.dossier_finalization_master_delivery_index_v7_5_13 import (
    build_master_delivery_index,
)
from socmint.dossier_finalization_master_delivery_index_v7_5_13 import (
    build_master_delivery_index_from_bundle,
)
from socmint.dossier_finalization_master_delivery_index_v7_5_13 import (
    build_master_delivery_index_from_zip_bytes,
)
from socmint.dossier_finalization_master_delivery_index_v7_5_13 import (
    recommended_delivery_action,
)
from socmint.dossier_finalization_master_delivery_index_v7_5_13 import (
    render_master_delivery_index_markdown,
)
from socmint.dossier_finalization_master_delivery_index_v7_5_13 import (
    summarize_master_delivery_index,
)


def verified_report():
    return {
        "schema": "socmint.v7_5_12.dossier_finalization_closeout_export_verification",
        "status": "verified",
        "verified": True,
        "failure_count": 0,
        "warning_count": 0,
        "required_files": ["README.md", "closeout_report.json"],
        "present_files": ["README.md", "closeout_report.json"],
        "missing_files": [],
        "unexpected_files": [],
        "manifest": {"file_count": 5, "files": []},
        "closeout_action": "closeout_ready",
        "verification_status": "verified",
        "failures": [],
        "warnings": [],
        "summary": {"status": "verified", "verified": True},
    }


def review_report():
    report = verified_report()
    report.update(
        {
            "status": "needs_human_review",
            "verified": False,
            "warning_count": 1,
            "closeout_action": "regenerate_export",
        }
    )
    report["warnings"] = [
        {
            "severity": "warn",
            "code": "non_closeout_ready",
            "path": "closeout_report.json",
            "detail": "Closeout export is structurally intact but not closeout-ready.",
            "action": "Complete human review before delivery.",
        }
    ]
    return report


def failed_report():
    report = verified_report()
    report.update({"status": "failed", "verified": False, "failure_count": 1})
    report["failures"] = [
        {
            "severity": "fail",
            "code": "sha256_mismatch",
            "path": "closeout_report.json",
            "detail": "Manifest SHA-256 does not match file bytes.",
            "action": "Regenerate the export.",
        }
    ]
    return report


def v759_report():
    return {
        "schema": "socmint.v7_5_9.dossier_finalization_handoff_export_verification",
        "status": "verified",
        "verified": True,
        "failure_count": 0,
        "warning_count": 0,
        "recommended_action": "archive_ready",
        "verification_status": "verified",
        "certificate_status": "valid",
        "missing_files": [],
        "unexpected_files": [],
        "failures": [],
        "warnings": [],
        "summary": {"status": "verified", "verified": True},
    }


def closeout_bundle():
    closeout = build_closeout_report(v759_report(), operator="analyst")
    return build_closeout_export_bundle(closeout, bundle_name="delivery-index-source")


def test_recommended_delivery_action_mapping():
    assert recommended_delivery_action(verified_report()) == "deliver_ready"
    assert recommended_delivery_action(review_report()) == "human_review_required"
    assert recommended_delivery_action(failed_report()) == "regenerate_export"


def test_builds_deliver_ready_index_from_verified_report():
    index = build_master_delivery_index(
        verified_report(), operator="analyst", notes="Ready."
    )

    assert (
        index["schema"] == "socmint.v7_5_13.dossier_finalization_master_delivery_index"
    )
    assert index["approved_line"] == "v7.5.13"
    assert index["delivery_action"] == "deliver_ready"
    assert index["verified"] is True
    assert index["operator"] == "analyst"
    assert index["notes"] == "Ready."


def test_builds_human_review_required_index_from_review_report():
    index = build_master_delivery_index(review_report())

    assert index["delivery_action"] == "human_review_required"
    assert index["verified"] is False
    assert index["warning_count"] == 1


def test_builds_regenerate_export_index_from_failed_report():
    index = build_master_delivery_index(failed_report())

    assert index["delivery_action"] == "regenerate_export"
    assert index["failure_count"] == 1


def test_builds_index_from_v7511_bundle():
    index = build_master_delivery_index_from_bundle(
        closeout_bundle(), operator="analyst"
    )

    assert index["delivery_action"] == "deliver_ready"
    assert index["verification_status"] == "verified"
    assert index["operator"] == "analyst"


def test_builds_index_from_v7511_zip_bytes():
    zip_bytes = build_closeout_export_zip(closeout_bundle())

    index = build_master_delivery_index_from_zip_bytes(zip_bytes)

    assert index["delivery_action"] == "deliver_ready"
    assert index["verified"] is True


def test_findings_combine_failures_and_warnings():
    report = failed_report()
    report["warnings"] = review_report()["warnings"]
    report["warning_count"] = 1

    index = build_master_delivery_index(report)

    assert len(index["findings"]) == 2
    assert {item["severity"] for item in index["findings"]} == {"fail", "warn"}


def test_summary_is_compact():
    index = build_master_delivery_index(verified_report())
    summary = summarize_master_delivery_index(index)

    assert (
        summary["schema"]
        == "socmint.v7_5_13.dossier_finalization_master_delivery_index.summary"
    )
    assert summary["delivery_action"] == "deliver_ready"
    assert "findings" not in summary
    assert "verification_summary" not in summary


def test_markdown_includes_required_headings():
    markdown = render_master_delivery_index_markdown(
        build_master_delivery_index(verified_report(), notes="Ready.")
    )

    assert "# SOCMINT v7.5.13 Master Dossier Delivery Index" in markdown
    assert "Delivery action: DELIVER_READY" in markdown
    assert "## Delivery Status" in markdown
    assert "## Closeout Export Verification" in markdown
    assert "## File Inventory" in markdown
    assert "## Findings" in markdown
    assert "## Operator Notes" in markdown


def test_file_inventory_is_preserved():
    report = verified_report()
    index = build_master_delivery_index(report)

    assert index["required_files"] == report["required_files"]
    assert index["present_files"] == report["present_files"]
    assert index["missing_files"] == []
    assert index["unexpected_files"] == []
    assert index["file_count"] == 5


def test_input_verification_report_is_not_mutated():
    report = verified_report()
    original = deepcopy(report)

    build_master_delivery_index(report)

    assert report == original
