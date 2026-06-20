from pathlib import Path

from src.socmint.administration_product_review_v28_7 import (
    REQUIRED_ROUTES,
    build_administration_product_review,
)


class _Route:
    def __init__(self, rule: str, methods=("GET",)):
        self.rule = rule
        self.methods = set(methods) | {"HEAD", "OPTIONS"}


def _fixture_tree(root: Path) -> None:
    from src.socmint.administration_product_review_v28_7 import (
        REQUIRED_ASSETS,
        REQUIRED_MODULES,
        REQUIRED_NOTES,
    )

    for item in (*REQUIRED_MODULES, *REQUIRED_ASSETS, *REQUIRED_NOTES):
        path = root / item
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture\n", encoding="utf-8")


def test_v28_7_product_review_ready_with_complete_journey(tmp_path):
    _fixture_tree(tmp_path)
    routes = [_Route(rule) for rule in REQUIRED_ROUTES]
    result = build_administration_product_review(tmp_path, routes=routes)
    assert result["status"] == "ready_for_browser_e2e"
    assert result["ready"] is True
    assert result["blocker_count"] == 0
    assert result["journey_step_count"] == 7
    assert all(item["ok"] for item in result["module_checks"])
    assert all(item["ok"] for item in result["asset_checks"])
    assert all(item["ok"] for item in result["release_note_checks"])
    assert all(item["registered"] for item in result["route_checks"])
    assert result["duplicate_routes"] == []
    assert result["migration_artifacts"] == []
    assert result["administrator_authorization_validated"] is True
    assert result["append_only_governance_validated"] is True
    assert result["credentials_and_secrets_excluded_validated"] is True
    assert result["source_records_mutated"] is False
    assert result["checkpoint_record_created"] is False
    assert result["next_action"] == "run_v28_browser_e2e"


def test_v28_7_product_review_blocks_missing_duplicate_and_migration(tmp_path):
    _fixture_tree(tmp_path)
    (tmp_path / "src/socmint/access_policy_workspace_v28_2.py").unlink()
    migration = tmp_path / "migrations/v28_7_bad.py"
    migration.parent.mkdir(parents=True, exist_ok=True)
    migration.write_text("bad\n", encoding="utf-8")
    routes = [
        _Route(rule) for rule in REQUIRED_ROUTES if rule != "/administration/operations"
    ]
    routes.extend([_Route("/administration"), _Route("/administration")])
    result = build_administration_product_review(tmp_path, routes=routes)
    assert result["status"] == "blocked"
    assert result["ready"] is False
    keys = {item["key"] for item in result["blockers"]}
    assert "missing_v28_module" in keys
    assert "missing_v28_route" in keys
    assert "duplicate_v28_route" in keys
    assert "unexpected_v28_migration" in keys
    assert result["next_action"] == "resolve_v28_product_blockers"
