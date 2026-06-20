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
    launch_operator_workflow_action,
)
from src.socmint.operator_workflow_action_receipt_v17_3 import (
    OPERATOR_WORKFLOW_ACTION_RECEIPT_SCHEMA,
)
from src.socmint.operator_workflow_action_receipt_v17_3 import (
    attach_operator_workflow_action_receipt,
)
from src.socmint.operator_workflow_action_receipt_v17_3 import (
    build_operator_workflow_action_receipt,
)
from src.socmint.unified_operator_workflow_dashboard_routes_v17_1 import (
    register_unified_operator_workflow_dashboard_routes_v17_1,
)
from tests.test_v15_case_delivery_workspace import ready_payload


FIXED_TIME = "2026-06-12T21:30:00+00:00"


def _app():
    app = create_app()
    register_operator_release_console_routes_v14(app)
    register_case_delivery_workspace_routes_v15(app)
    register_unified_operator_workflow_dashboard_routes_v17_1(app)
    return app


def _ready_payload(case_id="case-v17-3"):
    payload = ready_payload(
        operator="operator", issuer="release-lead", authorizer="delivery-lead"
    )
    payload["operations"] = build_case_delivery_operations(case_id, payload)
    return payload


def test_v17_3_builds_deterministic_action_receipt():
    action_result = {
        "status": "launched",
        "action": "open_case_delivery",
        "label": "Open case-delivery workspace",
        "confirmed": False,
        "requires_confirmation": False,
        "state_change": False,
        "action_plan": {
            "type": "navigation",
            "target": "/case-delivery?case_id=case-v17-3",
        },
        "blocker_count": 0,
        "next_action": "follow_action_plan",
    }
    first = build_operator_workflow_action_receipt(
        "case-v17-3",
        action_result,
        operator="operator",
        recorded_at=FIXED_TIME,
    )
    second = build_operator_workflow_action_receipt(
        "case-v17-3",
        action_result,
        operator="operator",
        recorded_at=FIXED_TIME,
    )

    assert first["schema"] == OPERATOR_WORKFLOW_ACTION_RECEIPT_SCHEMA
    assert first["action_receipt_id"] == second["action_receipt_id"]
    assert first["receipt_sha256"] == second["receipt_sha256"]
    assert first["action_target"] == "/case-delivery?case_id=case-v17-3"
    assert first["result_status"] == "launched"
    assert first["recorded_at"] == FIXED_TIME


def test_v17_3_receipt_records_confirmation_required_result():
    app = _app()
    action_result = launch_operator_workflow_action(
        "case-v17-3",
        {"action": "refresh_release_health", "dashboard_payload": _ready_payload()},
        routes=list(app.url_map.iter_rules()),
    )
    result = attach_operator_workflow_action_receipt(
        "case-v17-3",
        action_result,
        operator="operator",
        recorded_at=FIXED_TIME,
    )

    receipt = result["action_receipt"]
    assert result["status"] == "confirmation_required"
    assert receipt["result_status"] == "confirmation_required"
    assert receipt["requires_confirmation"] is True
    assert receipt["confirmed"] is False
    assert receipt["action_target"] is None


def test_v17_3_receipt_records_blocked_dispatch():
    app = _app()
    action_result = launch_operator_workflow_action(
        "case-v17-3-blocked",
        {
            "action": "dispatch_delivery_operations",
            "confirmed": True,
            "dashboard_payload": ready_payload(approval_decision="pending_review"),
        },
        routes=list(app.url_map.iter_rules()),
    )
    result = attach_operator_workflow_action_receipt(
        "case-v17-3-blocked",
        action_result,
        operator="operator",
        recorded_at=FIXED_TIME,
    )

    receipt = result["action_receipt"]
    assert result["status"] == "blocked"
    assert receipt["result_status"] == "blocked"
    assert receipt["confirmed"] is True
    assert receipt["state_change"] is True
    assert receipt["blocker_count"] > 0


def test_v17_3_action_route_returns_receipt_for_launched_action(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    client = _app().test_client()
    with client.session_transaction() as sess:
        sess["user"] = "operator"
        sess["_csrf_token"] = "test-csrf"

    response = client.post(
        "/api/v1/operator/workflow-dashboard/case-v17-3/actions",
        json={
            "action": "open_case_delivery",
            "recorded_at": FIXED_TIME,
            "dashboard_payload": _ready_payload(),
        },
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    receipt = payload["action_receipt"]
    assert receipt["operator"] == "operator"
    assert receipt["action"] == "open_case_delivery"
    assert receipt["result_status"] == "launched"
    assert receipt["action_receipt_id"]


def test_v17_3_action_route_returns_receipt_when_confirmation_required(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    client = _app().test_client()
    with client.session_transaction() as sess:
        sess["user"] = "operator"
        sess["_csrf_token"] = "test-csrf"

    response = client.post(
        "/api/v1/operator/workflow-dashboard/case-v17-3/actions",
        json={
            "action": "refresh_release_health",
            "recorded_at": FIXED_TIME,
            "dashboard_payload": _ready_payload(),
        },
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert response.status_code == 409
    payload = response.get_json()
    assert payload["action_receipt"]["result_status"] == "confirmation_required"
    assert payload["action_receipt"]["recorded_at"] == FIXED_TIME


def test_v17_3_release_note_and_changelog_are_present():
    note = Path("release/V17_3_OPERATOR_ACTION_RECEIPT_AUDIT_TRAIL.md").read_text(
        encoding="utf-8"
    )
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert "action_receipt_id" in note
    assert "/api/v1/operator/workflow-dashboard/<case_id>/actions" in note
    assert "v17.3 Operator Action Receipt / Audit Trail" in changelog
