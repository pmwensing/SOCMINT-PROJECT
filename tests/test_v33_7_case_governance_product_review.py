from flask import Flask

from src.socmint.case_governance_product_review_v33_7 import (
    REQUIRED_ROUTES,
    build_case_governance_product_review,
)


def test_v33_7_closes_when_required_routes_exist():
    result = build_case_governance_product_review(routes=sorted(REQUIRED_ROUTES))
    assert result["ready"] is True
    assert result["v33_closed"] is True
    assert result["missing_routes"] == []
    assert result["review_sha256"]


def test_v33_7_blocks_when_route_is_missing():
    result = build_case_governance_product_review(routes=[])
    assert result["ready"] is False
    assert result["status"] == "blocked"
    assert result["missing_routes"]


def test_v33_7_browser_contract_sections_are_stable():
    result = build_case_governance_product_review(routes=sorted(REQUIRED_ROUTES))
    assert result["browser_e2e_contract"]["workspace_sections_required"] == [
        "governance-summary",
        "action-queue",
        "audience_package_authorization",
        "delivery_receipt_feedback",
        "lifecycle-timeline",
    ]
