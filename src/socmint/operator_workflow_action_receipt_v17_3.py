from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from .case_delivery_handoff_package_v15_1 import canonical_json
from .case_delivery_handoff_package_v15_1 import sha256_text


OPERATOR_WORKFLOW_ACTION_RECEIPT_SCHEMA = "socmint.operator_workflow_action_receipt.v17_3"
VERSION = "v17.3.0"


def _timestamp(value: str | None = None) -> str:
    if value:
        return value
    return datetime.now(UTC).isoformat()


def _action_target(action_result: dict[str, Any]) -> str | None:
    plan = action_result.get("action_plan")
    if not isinstance(plan, dict):
        return None
    target = plan.get("target") or plan.get("command")
    return str(target) if target is not None else None


def build_operator_workflow_action_receipt(
    case_id: str,
    action_result: dict[str, Any],
    *,
    operator: str | None = None,
    recorded_at: str | None = None,
) -> dict[str, Any]:
    safe_result = deepcopy(action_result or {})
    timestamp = _timestamp(recorded_at)
    receipt_payload = {
        "schema": OPERATOR_WORKFLOW_ACTION_RECEIPT_SCHEMA,
        "version": VERSION,
        "case_id": case_id,
        "operator": operator or "unknown",
        "action": safe_result.get("action"),
        "label": safe_result.get("label"),
        "confirmed": safe_result.get("confirmed") is True,
        "requires_confirmation": safe_result.get("requires_confirmation") is True,
        "state_change": safe_result.get("state_change") is True,
        "action_target": _action_target(safe_result),
        "action_plan_type": (
            safe_result.get("action_plan", {}).get("type")
            if isinstance(safe_result.get("action_plan"), dict)
            else None
        ),
        "result_status": safe_result.get("status"),
        "result_next_action": safe_result.get("next_action"),
        "blocker_count": int(safe_result.get("blocker_count") or 0),
        "recorded_at": timestamp,
    }
    receipt_hash = sha256_text(canonical_json(receipt_payload))
    return {
        **receipt_payload,
        "receipt_sha256": receipt_hash,
        "action_receipt_id": sha256_text(
            canonical_json({**receipt_payload, "receipt_sha256": receipt_hash})
        ),
    }


def attach_operator_workflow_action_receipt(
    case_id: str,
    action_result: dict[str, Any],
    *,
    operator: str | None = None,
    recorded_at: str | None = None,
) -> dict[str, Any]:
    safe_result = deepcopy(action_result or {})
    safe_result["action_receipt"] = build_operator_workflow_action_receipt(
        case_id,
        safe_result,
        operator=operator,
        recorded_at=recorded_at,
    )
    return safe_result
