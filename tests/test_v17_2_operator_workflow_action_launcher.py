from __future__ import annotations

from pathlib import Path

from src.socmint.case_delivery_operations_v16_0 import build_case_delivery_operations
from src.socmint.case_delivery_workspace_routes_v15 import (
    register_case_delivery_workspace_routes_v15,
)
from src.socmint.dashboard import create_app
from src.socmint.operator_release_console_routes_v14 import (
    register_operator_release_console_routes_v14,
)
from src.socmint.operator_workflow_action_launcher_v17_2 import (
    OPERATOR_WORKFLOW_ACTION_LAUNCHER_SCHEMA,
)
from src.socmint.operator_workflow_action_launcher_v17_2 import (
    launch_operator_workflow_action,
)
from src.socmint.unified_operator_workflow_dashboard_routes_v17_1 import (
    register_unified_operator_workflow_dashboard_routes_v17_1,
)
from tests.test_v15_case_delivery_workspace import ready_payload


def _app():
    app = create_app()
    register_operator_release_console_routes_v14(app)
    register_case_delivery_workspace_routes_v15(app)
    register_unified_operator_workflow_dashboard_routes_v17_1(app)
    return app


def _ready_payload(case_id="case-v17-2"):
    payload = ready_payload(
        operator="operator", issuer="release-lead", authorizer="delivery-lead"
    )
    payload["operations"] = build_case_delivery_operations(case_id, payload)
    return payload


def test_v17_2_navigation_action_launches_without_confirmation():
    app = _app()
    result = launch_operator_workflow_action(
        "case-v17-2",
        {"action": "open_case_delivery", "dashboard_payload": _ready_payload()},
        routes=list(app.url_map.iter_rules()),
    )
    assert result["schema"] == OPERATOR_WORKFLOW_ACTION_LAUNCHER_SCHEMA
    assert result["status"] == "launched"
    assert result["requires_confirmation"] is False
    assert result["action_plan"]["type"] == "navigation"


def test_v17_2_refresh_requires_confirmation():
    app = _app()
    result = launch_operator_workflow_action(
        "case-v17-2",
        {"action": "refresh_release_health", "dashboard_payload": _ready_payload()},
        routes=list(app.url_map.iter_rules()),
    )
    assert result["status"] == "confirmation_required"
    assert result["next_action"] == "confirm_operator_action"


def test_v17_2_confirmed_refresh_returns_manual_command_plan():
    app = _app()
    result = launch_operator_workflow_action(
        "case-v17-2",
        {
            "action": "refresh_release_health",
            "confirmed": True,
            "dashboard_payload": _ready_payload(),
        },
        routes=list(app.url_map.iter_rules()),
    )
    assert result["status"] == "launched"
    assert result["action_plan"]["type"] == "manual_command"
    assert "refresh_operator_release_health" in result["action_plan"]["command"]


def test_v17_2_dispatch_requires_confirmation_and_readiness():
    app = _app()
    unconfirmed = launch_operator_workflow_action(
        "case-v17-2",
        {
            "action": "dispatch_delivery_operations",
            "dashboard_payload": _ready_payload(),
        },
        routes=list(app.url_map.iter_rules()),
    )
    confirmed = launch_operator_workflow_action(
        "case-v17-2",
        {
            "action": "dispatch_delivery_operations",
            "confirmed": True,
            "dashboard_payload": _ready_payload(),
        },
        routes=list(app.url_map.iter_rules()),
    )
    assert unconfirmed["status"] == "confirmation_required"
    assert confirmed["status"] == "launched"
    assert confirmed["action_plan"]["type"] == "state_change_request"
    assert confirmed["action_plan"]["confirmation_recorded"] is True


def test_v17_2_dispatch_blocks_when_case_not_ready():
    app = _app()
    result = launch_operator_workflow_action(
        "case-v17-2-blocked",
        {
            "action": "dispatch_delivery_operations",
            "confirmed": True,
            "dashboard_payload": ready_payload(approval_decision="pending_review"),
        },
        routes=list(app.url_map.iter_rules()),
    )
    assert result["status"] == "blocked"
    assert any(
        item["key"] == "delivery_operations_not_ready" for item in result["blockers"]
    )


def test_v17_2_action_route_requires_login(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    client = _app().test_client()
    with client.session_transaction() as sess:
        sess["_csrf_token"] = "test-csrf"
    response = client.post(
        "/api/v1/operator/workflow-dashboard/case-1/actions",
        json={"action": "open_case_delivery"},
        headers={"X-CSRF-Token": "test-csrf"},
    )
    assert response.status_code == 401


def test_v17_2_action_route_returns_confirmation_required(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    client = _app().test_client()
    with client.session_transaction() as sess:
        sess["user"] = "operator"
        sess["_csrf_token"] = "test-csrf"
    response = client.post(
        "/api/v1/operator/workflow-dashboard/case-1/actions",
        json={
            "action": "refresh_release_health",
            "dashboard_payload": _ready_payload("case-1"),
        },
        headers={"X-CSRF-Token": "test-csrf"},
    )
    assert response.status_code == 409
    assert response.get_json()["status"] == "confirmation_required"


def test_v17_2_release_note_changelog_and_controls_are_present():
    note = Path("release/V17_2_OPERATOR_WORKFLOW_ACTION_LAUNCHER.md").read_text(
        encoding="utf-8"
    )
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")
    template = Path(
        "src/socmint/templates/unified_operator_workflow_dashboard.html"
    ).read_text(encoding="utf-8")
    assert "/api/v1/operator/workflow-dashboard/<case_id>/actions" in note
    assert "v17.2 Operator Workflow Action Launcher" in changelog
    assert "Operator Action Launcher" in template
