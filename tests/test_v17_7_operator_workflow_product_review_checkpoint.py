from __future__ import annotations

from pathlib import Path

from src.socmint.case_delivery_workspace_routes_v15 import register_case_delivery_workspace_routes_v15
from src.socmint.dashboard import create_app
from src.socmint.operator_release_console_routes_v14 import register_operator_release_console_routes_v14
from src.socmint.operator_workflow_product_review_checkpoint_v17_7 import (
    OPERATOR_WORKFLOW_PRODUCT_REVIEW_CHECKPOINT_SCHEMA,
    build_operator_workflow_product_review_checkpoint,
)
from src.socmint.unified_operator_workflow_dashboard_routes_v17_1 import (
    register_unified_operator_workflow_dashboard_routes_v17_1,
)


def _app():
    app = create_app()
    register_operator_release_console_routes_v14(app)
    register_case_delivery_workspace_routes_v15(app)
    register_unified_operator_workflow_dashboard_routes_v17_1(app)
    return app


def test_v17_7_product_review_checkpoint_is_ready():
    app = _app()

    result = build_operator_workflow_product_review_checkpoint(
        routes=list(app.url_map.iter_rules())
    )

    assert result["schema"] == OPERATOR_WORKFLOW_PRODUCT_REVIEW_CHECKPOINT_SCHEMA
    assert result["status"] == "ready_for_browser_validation"
    assert result["ready"] is True
    assert result["blocker_count"] == 0
    assert result["duplicate_routes"] == []
    assert result["migration_artifacts"] == []
    assert result["next_action"] == "run_browser_e2e_validation"
    assert all(item["ok"] for item in result["module_checks"])
    assert all(item["ok"] for item in result["asset_checks"])
    assert all(item["ok"] for item in result["release_note_checks"])
    assert all(item["registered"] for item in result["route_checks"])


def test_v17_7_product_review_checkpoint_route_requires_login(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    client = _app().test_client()

    response = client.get("/api/v1/operator/workflow-dashboard/product-review-checkpoint")

    assert response.status_code == 401


def test_v17_7_product_review_checkpoint_route_returns_ready(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    client = _app().test_client()
    with client.session_transaction() as sess:
        sess["user"] = "operator"

    response = client.get("/api/v1/operator/workflow-dashboard/product-review-checkpoint")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ready"] is True
    assert payload["status"] == "ready_for_browser_validation"


def test_v17_7_browser_runner_has_real_browser_checks():
    runner_path = Path("scripts/run_v17_7_operator_dashboard_browser_e2e.py")
    source = runner_path.read_text(encoding="utf-8")

    compile(source, str(runner_path), "exec")
    assert "webdriver.Chrome" in source
    assert "webdriver.Firefox" in source
    assert "authenticated_dashboard_render" in source
    assert "unsafe_dispatch_disabled" in source
    assert "action_result_feedback" in source
    assert "history_updates_after_action" in source
    assert "manual_history_refresh" in source
    assert "navigation_action" in source
    assert "artifacts/v17_7_operator_dashboard_browser_e2e.json" in source


def test_v17_7_release_note_and_changelog_are_present():
    note = Path("release/V17_7_PRODUCT_REVIEW_AND_BROWSER_E2E_VALIDATION.md").read_text(encoding="utf-8")
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert "product-review-checkpoint" in note
    assert "run_v17_7_operator_dashboard_browser_e2e.py" in note
    assert "v17.7 Product Review Checkpoint and Browser-Level E2E Validation" in changelog
