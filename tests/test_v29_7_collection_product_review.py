from pathlib import Path

from src.socmint.collection_product_review_v29_7 import (
    REQUIRED_ROUTES,
    build_collection_product_review,
)


class Route:
    def __init__(self, rule, methods=("GET",)):
        self.rule = rule
        self.methods = set(methods) | {"HEAD", "OPTIONS"}


def test_v29_7_product_review_ready_for_browser_e2e():
    routes = [Route(rule) for rule in REQUIRED_ROUTES]
    result = build_collection_product_review(Path("."), routes=routes)
    assert result["status"] == "ready_for_browser_e2e"
    assert result["ready"] is True
    assert result["blocker_count"] == 0
    assert result["journey_step_count"] == 7
    assert result["connector_execution_unavailable_validated"] is True
    assert result["automatic_dossier_mutation_unavailable_validated"] is True


def test_v29_7_product_review_blocks_missing_assets_and_routes(tmp_path):
    result = build_collection_product_review(tmp_path, routes=[])
    assert result["status"] == "blocked"
    assert result["ready"] is False
    keys = {item["key"] for item in result["blockers"]}
    assert "missing_v29_module" in keys
    assert "missing_v29_asset" in keys
    assert "missing_v29_route" in keys
