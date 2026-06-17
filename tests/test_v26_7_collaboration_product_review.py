from pathlib import Path

from src.socmint.collaboration_product_review_v26_7 import REQUIRED_ROUTES, build_collaboration_product_review


class Route:
    def __init__(self, rule):
        self.rule = rule
        self.methods = {"GET", "HEAD", "OPTIONS"}


def _touch(root: Path, path: str) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("ok", encoding="utf-8")


def test_v26_7_ready_product_checkpoint(tmp_path):
    from src.socmint.collaboration_product_review_v26_7 import REQUIRED_ASSETS, REQUIRED_MODULES, REQUIRED_NOTES
    for path in REQUIRED_MODULES + REQUIRED_ASSETS + REQUIRED_NOTES:
        _touch(tmp_path, path)
    result = build_collaboration_product_review(tmp_path, routes=[Route(rule) for rule in REQUIRED_ROUTES])
    assert result["status"] == "ready_for_browser_e2e"
    assert result["blocker_count"] == 0
    assert result["journey_step_count"] == 7
    assert result["v26_closed_when_browser_e2e_passes"] is True
    assert result["source_records_mutated"] is False


def test_v26_7_detects_blockers(tmp_path):
    migration = tmp_path / "migrations" / "v26_bad.py"
    migration.parent.mkdir(parents=True)
    migration.write_text("bad", encoding="utf-8")
    result = build_collaboration_product_review(tmp_path, routes=[Route("/collaboration"), Route("/collaboration")])
    keys = {item["key"] for item in result["blockers"]}
    assert {"missing_v26_module", "missing_v26_route", "duplicate_v26_route", "unexpected_v26_migration"} <= keys
