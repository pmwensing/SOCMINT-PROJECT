from pathlib import Path

from src.socmint.analytic_product_review_v30_7 import REQUIRED_ASSETS, REQUIRED_MODULES, build_analytic_product_review


class Route:
    def __init__(self, rule: str, methods: set[str] | None = None):
        self.rule = rule
        self.methods = methods or {"GET"}


def test_v30_7_product_review_ready_when_manifest_and_routes_exist(tmp_path):
    for item in (*REQUIRED_MODULES, *REQUIRED_ASSETS):
        path = tmp_path / item
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("ok", encoding="utf-8")
    routes = [
        Route("/analytic-review"),
        Route("/api/v1/analytic-review"),
        Route("/api/v1/analytic-review/claims"),
        Route("/api/v1/analytic-review/conflicts"),
        Route("/api/v1/analytic-review/human-reviews"),
        Route("/api/v1/analytic-review/dossier-contributions"),
        Route("/analytic-review/product-review"),
        Route("/api/v1/analytic-review/product-review-checkpoint"),
    ]

    result = build_analytic_product_review(tmp_path, routes=routes)

    assert result["ready"] is True
    assert result["blocker_count"] == 0
    assert result["journey_step_count"] == 7
    assert result["automatic_dossier_mutation_unavailable_validated"] is True


def test_v30_7_product_review_blocks_missing_assets_routes_and_migrations(tmp_path):
    for item in REQUIRED_MODULES:
        path = tmp_path / item
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("ok", encoding="utf-8")
    migration = tmp_path / "migrations" / "v30_unexpected.py"
    migration.parent.mkdir(parents=True, exist_ok=True)
    migration.write_text("unexpected", encoding="utf-8")

    result = build_analytic_product_review(tmp_path, routes=[])

    assert result["ready"] is False
    keys = {item["key"] for item in result["blockers"]}
    assert "missing_v30_asset" in keys
    assert "missing_v30_route" in keys
    assert "unexpected_v30_migration" in keys
