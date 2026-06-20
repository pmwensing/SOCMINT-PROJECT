import pytest

from socmint.connector_compliance_v7_5 import assert_connector_compliance
from socmint.connector_compliance_v7_5 import build_connector_compliance_report


def connector_entry(**overrides):
    data = {
        "name": "manual_source",
        "version": "1.0",
        "supported_seed_types": ["name", "url"],
        "requires_network": False,
        "requires_api_key": False,
        "risk_level": "low",
        "source_method": "analyst_supplied",
        "rate_limit_policy": {"requests_per_minute": 0},
        "policy_metadata": {"human_review_required": False, "public_source_only": True},
        "dry_run_supported": True,
    }
    data.update(overrides)
    return data


def test_connector_report_passes_complete_metadata():
    report = build_connector_compliance_report([connector_entry()])

    assert report["schema"] == "socmint.v7_5.connector_compliance"
    assert report["status"] == "pass"
    assert report["connector_count"] == 1
    assert report["finding_count"] == 0
    assert report["supported_seed_type_counts"]["url"] == 1


def test_connector_report_fails_missing_policy_metadata_and_test_mode():
    report = build_connector_compliance_report(
        [
            connector_entry(
                name="incomplete", policy_metadata={}, dry_run_supported=False
            )
        ]
    )

    assert report["status"] == "fail"
    checks = {item["check"] for item in report["findings"]}
    assert "required_fields" in checks
    assert "dry_run_supported" in checks


def test_elevated_risk_connector_requires_review_flag():
    report = build_connector_compliance_report(
        [
            connector_entry(
                name="review_required_adapter",
                risk_level="high",
                policy_metadata={
                    "human_review_required": False,
                    "public_source_only": True,
                },
            )
        ]
    )

    assert report["status"] == "fail"
    assert any(item["check"] == "high_risk_human_review" for item in report["findings"])


def test_assert_connector_compliance_raises_on_failure():
    with pytest.raises(AssertionError):
        assert_connector_compliance([connector_entry(name="incomplete", version="")])
