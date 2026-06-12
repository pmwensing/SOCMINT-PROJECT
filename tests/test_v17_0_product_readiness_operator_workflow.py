from __future__ import annotations

from pathlib import Path

from src.socmint.dashboard import create_app
from src.socmint.operator_release_console_routes_v14 import register_operator_release_console_routes_v14
from src.socmint.product_readiness_operator_workflow_v17_0 import PRODUCT_READINESS_OPERATOR_WORKFLOW_SCHEMA
from src.socmint.product_readiness_operator_workflow_v17_0 import build_product_readiness_operator_workflow_snapshot
from src.socmint.case_delivery_workspace_routes_v15 import register_case_delivery_workspace_routes_v15


def _app_with_product_routes():
    app = create_app()
    register_case_delivery_workspace_routes_v15(app)
    register_operator_release_console_routes_v14(app)
    return app


def test_v17_0_product_readiness_snapshot_is_ready_with_product_routes():
    app = _app_with_product_routes()

    result = build_product_readiness_operator_workflow_snapshot(routes=list(app.url_map.iter_rules()))

    assert result["schema"] == PRODUCT_READINESS_OPERATOR_WORKFLOW_SCHEMA
    assert result["status"] == "ready"
    assert result["ready"] is True
    assert result["operator_workflow_ready"] is True
    assert result["case_delivery_ux_ready"] is True
    assert result["release_console_aligned"] is True
    assert result["operations_route_ready"] is True
    assert result["recovery_chain_closed"] is True
    assert result["end_to_end_ready"] is True
    assert result["blocker_count"] == 0
    assert result["next_action"] == "resume_product_level_delivery_work"


def test_v17_0_product_readiness_blocks_missing_release_console_route():
    app = create_app()
    register_case_delivery_workspace_routes_v15(app)

    result = build_product_readiness_operator_workflow_snapshot(routes=list(app.url_map.iter_rules()))

    assert result["status"] == "blocked"
    assert result["release_console_aligned"] is False
    assert any(blocker["key"] == "missing_product_route" for blocker in result["blockers"])


def test_v17_0_product_readiness_route_requires_login(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = _app_with_product_routes()
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["_csrf_token"] = "test-csrf"

    response = client.post(
        "/api/v1/product-readiness/operator-workflow",
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert response.status_code == 401


def test_v17_0_product_readiness_route_returns_ready(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = _app_with_product_routes()
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user"] = "operator"
        sess["_csrf_token"] = "test-csrf"

    response = client.post(
        "/api/v1/product-readiness/operator-workflow",
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ready"
    assert payload["operator_workflow_ready"] is True
    assert payload["end_to_end_ready"] is True
    assert payload["next_action"] == "resume_product_level_delivery_work"


def test_v17_0_release_note_and_changelog_are_present():
    note = Path("release/V17_0_PRODUCT_READINESS_OPERATOR_WORKFLOW_INTEGRATION.md").read_text(encoding="utf-8")
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert "/api/v1/product-readiness/operator-workflow" in note
    assert "v17.0 Product Readiness / Operator Workflow Integration" in changelog
