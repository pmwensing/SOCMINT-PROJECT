from pathlib import Path

from src.socmint.cross_case_intelligence_product_review_v25_7 import (
    REQUIRED_ASSETS,
    REQUIRED_MODULES,
    REQUIRED_NOTES,
    REQUIRED_ROUTES,
    build_cross_case_intelligence_product_review,
)


def test_v25_7_product_review_files_are_complete():
    result = build_cross_case_intelligence_product_review(Path("."))

    assert result["ready"] is True
    assert result["status"] == "ready_for_browser_e2e"
    assert result["blocker_count"] == 0
    assert len(result["module_checks"]) == len(REQUIRED_MODULES)
    assert len(result["asset_checks"]) == len(REQUIRED_ASSETS)
    assert len(result["release_note_checks"]) == len(REQUIRED_NOTES)
    assert all(item["ok"] for item in result["module_checks"])
    assert all(item["ok"] for item in result["asset_checks"])
    assert all(item["ok"] for item in result["release_note_checks"])
    assert result["migration_artifacts"] == []
    assert result["journey_step_count"] == 7
    assert [item["step"] for item in result["journey"]] == [
        "candidate_discovery",
        "analyst_review_decision",
        "confirmed_link_registration",
        "relationship_graph",
        "impact_analysis",
        "history_audit",
        "metrics_confidence",
    ]
    assert result["access_controls_validated"] is True
    assert result["preservation_boundaries_validated"] is True
    assert result["confidence_interpretation_validated"] is True
    assert result["source_records_mutated"] is False
    assert result["checkpoint_record_created"] is False
    assert result["v25_closed_when_browser_e2e_passes"] is True


def test_v25_7_product_review_detects_missing_route_and_duplicate():
    class Route:
        def __init__(self, rule, methods):
            self.rule = rule
            self.methods = methods

    routes = [Route(rule, {"GET"}) for rule in REQUIRED_ROUTES[:-1]]
    routes.extend(
        [
            Route("/cross-case-intelligence", {"GET"}),
            Route("/cross-case-intelligence", {"GET"}),
        ]
    )

    result = build_cross_case_intelligence_product_review(Path("."), routes=routes)
    keys = {item["key"] for item in result["blockers"]}

    assert result["ready"] is False
    assert result["status"] == "blocked"
    assert "missing_v25_route" in keys
    assert "duplicate_v25_route" in keys
    assert result["next_action"] == "resolve_v25_product_blockers"
