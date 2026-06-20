from pathlib import Path

from src.socmint.portfolio_product_review_v24_7 import (
    REQUIRED_ASSETS,
    REQUIRED_MODULES,
    REQUIRED_NOTES,
    REQUIRED_ROUTES,
    build_portfolio_product_review,
)


def test_v24_7_product_review_files_are_complete():
    result = build_portfolio_product_review(Path("."))
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
    assert result["source_records_mutated"] is False
    assert result["checkpoint_record_created"] is False


def test_v24_7_product_review_detects_missing_route_and_duplicate():
    class Route:
        def __init__(self, rule, methods):
            self.rule = rule
            self.methods = methods

    routes = [Route(rule, {"GET"}) for rule in REQUIRED_ROUTES[:-1]]
    routes.extend(
        [
            Route("/portfolio-operations", {"GET"}),
            Route("/portfolio-operations", {"GET"}),
        ]
    )
    result = build_portfolio_product_review(Path("."), routes=routes)
    keys = {item["key"] for item in result["blockers"]}
    assert result["ready"] is False
    assert result["status"] == "blocked"
    assert "missing_v24_route" in keys
    assert "duplicate_v24_route" in keys
    assert result["next_action"] == "resolve_v24_product_blockers"
