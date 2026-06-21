from __future__ import annotations

from copy import deepcopy
from typing import Any

from .operator_release_console_v14 import RELEASE_HEALTH_REFRESH_COMMAND
from .unified_operator_workflow_dashboard_v17_1 import (
    build_unified_operator_workflow_dashboard,
)


OPERATOR_WORKFLOW_ACTION_LAUNCHER_SCHEMA = (
    "socmint.operator_workflow_action_launcher.v17_2"
)
VERSION = "v17.2.0"

NAVIGATION_ACTIONS = {
    "open_case_delivery": {
        "label": "Open case-delivery workspace",
        "state_change": False,
    },
    "open_release_console": {
        "label": "Open operator release console",
        "state_change": False,
    },
    "review_blockers": {
        "label": "Review unified workflow blockers",
        "state_change": False,
    },
}

CONFIRMED_ACTIONS = {
    "refresh_release_health": {
        "label": "Refresh operator release health",
        "state_change": True,
    },
    "dispatch_delivery_operations": {
        "label": "Dispatch delivery operations",
        "state_change": True,
    },
}

SUPPORTED_ACTIONS = {**NAVIGATION_ACTIONS, **CONFIRMED_ACTIONS}


def _blocker(key: str, detail: str) -> dict[str, str]:
    return {"key": key, "detail": detail}


def _navigation_target(action: str, case_id: str) -> str:
    if action == "open_case_delivery":
        return f"/case-delivery?case_id={case_id}"
    if action == "open_release_console":
        return "/operator/release-console"
    return f"/operator/workflow-dashboard?case_id={case_id}#active-blockers"


def _dispatch_ready(dashboard: dict[str, Any]) -> bool:
    summary = (
        dashboard.get("summary") if isinstance(dashboard.get("summary"), dict) else {}
    )
    return bool(
        summary.get("case_delivery_ready")
        and summary.get("recovery_chain_closed")
        and summary.get("operations_dispatchable")
    )


def launch_operator_workflow_action(
    case_id: str,
    payload: dict[str, Any] | None = None,
    *,
    routes: list[Any] | None = None,
) -> dict[str, Any]:
    safe_payload = deepcopy(payload or {})
    action = str(safe_payload.get("action") or "").strip()
    confirmed = safe_payload.get("confirmed") is True or str(
        safe_payload.get("confirmed") or ""
    ).lower() in {
        "1",
        "true",
        "yes",
        "confirmed",
    }
    dashboard_payload = safe_payload.get("dashboard_payload")
    if not isinstance(dashboard_payload, dict):
        dashboard_payload = {
            key: value
            for key, value in safe_payload.items()
            if key not in {"action", "confirmed", "operator", "dashboard_payload"}
        }
    dashboard = build_unified_operator_workflow_dashboard(
        case_id,
        dashboard_payload,
        routes=routes,
    )
    blockers: list[dict[str, str]] = []

    if action not in SUPPORTED_ACTIONS:
        blockers.append(
            _blocker(
                "unsupported_action",
                f"unsupported operator workflow action: {action or 'missing'}",
            )
        )
        return {
            "schema": OPERATOR_WORKFLOW_ACTION_LAUNCHER_SCHEMA,
            "version": VERSION,
            "case_id": case_id,
            "status": "blocked",
            "action": action or None,
            "requires_confirmation": False,
            "confirmed": confirmed,
            "state_change": False,
            "action_plan": None,
            "blocker_count": len(blockers),
            "blockers": blockers,
            "dashboard": dashboard,
            "next_action": "choose_supported_operator_action",
        }

    definition = SUPPORTED_ACTIONS[action]
    requires_confirmation = action in CONFIRMED_ACTIONS
    if requires_confirmation and not confirmed:
        return {
            "schema": OPERATOR_WORKFLOW_ACTION_LAUNCHER_SCHEMA,
            "version": VERSION,
            "case_id": case_id,
            "status": "confirmation_required",
            "action": action,
            "label": definition["label"],
            "requires_confirmation": True,
            "confirmed": False,
            "state_change": True,
            "action_plan": None,
            "blocker_count": 0,
            "blockers": [],
            "dashboard": dashboard,
            "next_action": "confirm_operator_action",
        }

    if action in NAVIGATION_ACTIONS:
        target = _navigation_target(action, case_id)
        action_plan = {
            "type": "navigation",
            "target": target,
            "method": "GET",
            "safe_to_launch": True,
        }
    elif action == "refresh_release_health":
        action_plan = {
            "type": "manual_command",
            "command": RELEASE_HEALTH_REFRESH_COMMAND,
            "target": "/operator/release-console",
            "method": "operator_confirmed",
            "safe_to_launch": True,
        }
    else:
        if not _dispatch_ready(dashboard):
            blockers.append(
                _blocker(
                    "delivery_operations_not_ready",
                    "case delivery, recovery closure, and operations dispatchability must all be ready",
                )
            )
            return {
                "schema": OPERATOR_WORKFLOW_ACTION_LAUNCHER_SCHEMA,
                "version": VERSION,
                "case_id": case_id,
                "status": "blocked",
                "action": action,
                "label": definition["label"],
                "requires_confirmation": True,
                "confirmed": True,
                "state_change": True,
                "action_plan": None,
                "blocker_count": len(blockers),
                "blockers": blockers,
                "dashboard": dashboard,
                "next_action": dashboard.get("next_action")
                or "resolve_operator_workflow_blockers",
            }
        action_plan = {
            "type": "state_change_request",
            "target": f"/api/v1/case-delivery/{case_id}/operations",
            "method": "POST",
            "safe_to_launch": True,
            "confirmation_recorded": True,
            "operation_id": dashboard.get("operations", {})
            .get("payload", {})
            .get("operation_id"),
        }

    return {
        "schema": OPERATOR_WORKFLOW_ACTION_LAUNCHER_SCHEMA,
        "version": VERSION,
        "case_id": case_id,
        "status": "launched",
        "action": action,
        "label": definition["label"],
        "requires_confirmation": requires_confirmation,
        "confirmed": confirmed,
        "state_change": bool(definition["state_change"]),
        "action_plan": action_plan,
        "blocker_count": 0,
        "blockers": [],
        "dashboard": dashboard,
        "next_action": "follow_action_plan",
    }


def launch_operator_workflow_action_from_request(
    case_id: str, payload: dict[str, Any]
) -> dict[str, Any]:
    return launch_operator_workflow_action(case_id, payload)
