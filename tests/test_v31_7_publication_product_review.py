from pathlib import Path

from src.socmint.publication_product_review_v31_7 import (
    REQUIRED_ASSETS,
    REQUIRED_MODULES,
    REQUIRED_ROUTES,
    build_publication_product_review,
)


class Route:
    def __init__(self, rule: str):
        self.rule = rule
        self.methods = {"GET"}


def test_v31_7_product_review_ready_when_contract_complete(tmp_path: Path):
    for item in (*REQUIRED_MODULES, *REQUIRED_ASSETS):
        path = tmp_path / item
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("ok", encoding="utf-8")

    result = build_publication_product_review(
        tmp_path,
        routes=[Route(rule) for rule in REQUIRED_ROUTES],
    )

    assert result["ready"] is True
    assert result["status"] == "ready_for_browser_e2e"
    assert result["journey_step_count"] == 7
    assert result["blocker_count"] == 0
    assert result["supersession_preserves_history_validated"] is True


def test_v31_7_product_review_reports_missing_contract(tmp_path: Path):
    result = build_publication_product_review(tmp_path, routes=[])

    assert result["ready"] is False
    assert result["blocker_count"] > 0
    keys = {item["key"] for item in result["blockers"]}
    assert "missing_v31_module" in keys
    assert "missing_v31_asset" in keys
    assert "missing_v31_route" in keys
