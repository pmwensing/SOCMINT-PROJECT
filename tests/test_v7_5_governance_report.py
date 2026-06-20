import pytest

from socmint.policy_coverage_v7_5 import assert_policy_coverage
from socmint.policy_coverage_v7_5 import build_policy_coverage_report


def complete_rows():
    names = [
        "dossier_build",
        "dossier_export",
        "connector_run",
        "recursive_run",
        "artifact_upload",
        "artifact_download",
        "retention_run",
    ]
    return [
        {"operation": name, "decision": "allow", "case_id": "case-1"} for name in names
    ]


def test_report_passes_complete_rows():
    report = build_policy_coverage_report(complete_rows())

    assert report["schema"] == "socmint.v7_5.policy_coverage"
    assert report["status"] == "pass"
    assert report["missing_operation_count"] == 0
    assert report["operation_counts"]["dossier_export"] == 1


def test_report_lists_missing_rows():
    report = build_policy_coverage_report(
        [{"operation": "dossier_build", "decision": "allow", "case_id": "case-1"}]
    )

    assert report["status"] == "fail"
    assert "connector_run" in report["missing_operations"]
    assert report["missing_operation_count"] >= 1


def test_report_lists_unrecognized_decision():
    rows = complete_rows()
    rows[0] = {"operation": "dossier_build", "decision": "unknown", "case_id": "case-1"}
    report = build_policy_coverage_report(rows)

    assert report["status"] == "fail"
    assert any(item["check"] == "decision" for item in report["findings"])


def test_report_warns_unscoped_row():
    rows = complete_rows()
    rows[0] = {"operation": "dossier_build", "decision": "allow"}
    report = build_policy_coverage_report(rows)

    assert report["status"] == "warn"
    assert any(item["check"] == "scope" for item in report["findings"])


def test_assert_helper_raises_on_failure():
    with pytest.raises(AssertionError):
        assert_policy_coverage([])
