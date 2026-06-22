from pathlib import Path
from types import SimpleNamespace

from src.socmint.dissemination_product_review_v32_7 import (
    REQUIRED_ASSETS,
    REQUIRED_MODULES,
    REQUIRED_ROUTES,
    build_dissemination_product_review,
)


def _write_required(root: Path) -> None:
    for item in (*REQUIRED_MODULES, *REQUIRED_ASSETS):
        path = root / item
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("placeholder", encoding="utf-8")


def _routes():
    return [
        SimpleNamespace(rule=rule, methods={"GET", "HEAD", "OPTIONS"})
        for rule in REQUIRED_ROUTES
    ]


def test_v32_7_checkpoint_ready_when_contract_complete(tmp_path):
    _write_required(tmp_path)

    result = build_dissemination_product_review(
        tmp_path,
        routes=_routes(),
    )

    assert result["status"] == "ready_for_browser_e2e"
    assert result["ready"] is True
    assert result["blocker_count"] == 0
    assert result["journey_step_count"] == 10
    assert result["migration_artifacts"] == []
    assert result["feedback_isolation_validated"] is True
    assert result["recall_preserves_history_validated"] is True
    assert result["destructive_retention_unavailable_validated"] is True


def test_v32_7_checkpoint_reports_missing_route_and_asset(tmp_path):
    _write_required(tmp_path)
    missing_asset = tmp_path / REQUIRED_ASSETS[-1]
    missing_asset.unlink()
    routes = _routes()[:-1]

    result = build_dissemination_product_review(
        tmp_path,
        routes=routes,
    )

    assert result["status"] == "blocked"
    assert result["ready"] is False
    keys = {item["key"] for item in result["blockers"]}
    assert "missing_v32_asset" in keys
    assert "missing_v32_route" in keys
