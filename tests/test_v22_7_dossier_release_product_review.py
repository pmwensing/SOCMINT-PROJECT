from pathlib import Path

from src.socmint.dossier_release_product_review_v22_7 import (
    REQUIRED_ASSETS,
    REQUIRED_MODULES,
    REQUIRED_NOTES,
    REQUIRED_ROUTES,
    build_dossier_release_product_review,
)


def test_v22_7_product_review_files_are_complete():
    result = build_dossier_release_product_review(Path("."))
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


def test_v22_7_product_review_detects_missing_route_and_duplicate():
    class Route:
        def __init__(self, rule, methods):
            self.rule = rule
            self.methods = methods

    routes = [Route(route, {"GET"}) for route in REQUIRED_ROUTES[:-1]]
    routes.extend(
        [
            Route("/dossier-release/<case_id>", {"GET"}),
            Route("/dossier-release/<case_id>", {"GET"}),
        ]
    )
    result = build_dossier_release_product_review(Path("."), routes=routes)
    keys = {item["key"] for item in result["blockers"]}
    assert result["ready"] is False
    assert "missing_v22_route" in keys
    assert "duplicate_v22_route" in keys
