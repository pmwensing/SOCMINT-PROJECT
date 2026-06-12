from __future__ import annotations

from copy import deepcopy
from typing import Any

from .case_delivery_handoff_package_v15_1 import canonical_json
from .case_delivery_handoff_package_v15_1 import sha256_text
from .case_delivery_recovery_v16_3 import build_case_delivery_recovery_from_request


CASE_DELIVERY_RECOVERY_ACTION_RECEIPT_SCHEMA = "socmint.case_delivery_recovery_action_receipt.v16_4"
CASE_DELIVERY_RECOVERY_ACTION_RECEIPT_RESULT_SCHEMA = "socmint.case_delivery_recovery_action_receipt.v16_4.result"
VERSION = "v16.4.0"

VALID_DECISIONS = {"retry", "remediate", "escalate", "hold"}
COMPLETED_STATUSES = {"completed", "confirmed", "resolved", "acknowledged"}
OPEN_STATUSES = {"pending", "in_progress", "queued", "deferred"}
VALID_ACTION_STATUSES = COMPLETED_STATUSES | OPEN_STATUSES


def _blocker(key: str, detail: str) -> dict[str, Any]:
    return {"key": key, "detail": detail}


def _normalized_status(action: dict[str, Any] | None) -> str:
    if not isinstance(action, dict):
        return "pending"
    status = str(action.get("status") or action.get("action_status") or "pending").strip().lower()
    return status or "pending"


def _action_operator(action: dict[str, Any] | None, fallback: str | None) -> str:
    if isinstance(action, dict) and isinstance(action.get("operator"), str) and action["operator"].strip():
        return action["operator"].strip()
    return fallback or "unassigned"


def _action_detail(action: dict[str, Any] | None) -> str:
    if isinstance(action, dict) and isinstance(action.get("detail"), str):
        return action["detail"]
    if isinstance(action, dict) and isinstance(action.get("completion_detail"), str):
        return action["completion_detail"]
    return ""


def _action_matches_recovery(action: dict[str, Any], recovery: dict[str, Any]) -> bool:
    recovery_id = action.get("recovery_id")
    if recovery_id and recovery_id == recovery.get("recovery_id"):
        return True
    return (
        not recovery_id
        and action.get("decision") == recovery.get("decision")
        and action.get("exception_id") == recovery.get("exception_id")
    )


def _find_action(recovery: dict[str, Any], actions: list[dict[str, Any]]) -> dict[str, Any] | None:
    for action in actions:
        if _action_matches_recovery(action, recovery):
            return action
    return None


def _receipt_rows(recoveries: list[dict[str, Any]], actions: list[dict[str, Any]], operator: str | None) -> list[dict[str, Any]]:
    rows = []
    for sequence, recovery in enumerate(recoveries, start=1):
        if not isinstance(recovery, dict):
            continue
        decision = recovery.get("decision")
        action = _find_action(recovery, actions) or {}
        action_status = _normalized_status(action)
        payload = {
            "sequence": sequence,
            "recovery_id": recovery.get("recovery_id"),
            "exception_id": recovery.get("exception_id"),
            "attempt_id": recovery.get("attempt_id"),
            "category": recovery.get("category"),
            "decision": decision,
            "queue_state": recovery.get("queue_state"),
            "recommendation": recovery.get("recommendation"),
            "operator": _action_operator(action, operator),
            "action_status": action_status,
            "completed": action_status in COMPLETED_STATUSES,
            "detail": _action_detail(action),
        }
        rows.append({**payload, "action_receipt_id": sha256_text(canonical_json(payload))})
    return rows


def _status(rows: list[dict[str, Any]], blockers: list[dict[str, Any]]) -> str:
    if blockers:
        return "blocked"
    if not rows:
        return "no_action_required"
    if all(row.get("completed") is True for row in rows):
        return "completed"
    if any(row.get("completed") is True for row in rows):
        return "partially_completed"
    return "pending"


def _invalid_action_blockers(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blockers = []
    for row in rows:
        if row.get("action_status") not in VALID_ACTION_STATUSES:
            blockers.append(
                _blocker(
                    "invalid_action_status",
                    f"action status for recovery {row.get('recovery_id') or row.get('sequence')} is not supported",
                )
            )
        if row.get("decision") not in VALID_DECISIONS:
            blockers.append(
                _blocker(
                    "invalid_recovery_decision",
                    f"recovery decision for recovery {row.get('recovery_id') or row.get('sequence')} is not supported",
                )
            )
    return blockers


def build_case_delivery_recovery_action_receipt(
    case_id: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    safe_payload = deepcopy(payload or {})
    recovery = (
        deepcopy(safe_payload.get("recovery"))
        if isinstance(safe_payload.get("recovery"), dict)
        else build_case_delivery_recovery_from_request(case_id, safe_payload)
    )
    recoveries = recovery.get("operator_recovery_queue") if isinstance(recovery.get("operator_recovery_queue"), list) else []
    actions = safe_payload.get("actions") if isinstance(safe_payload.get("actions"), list) else []
    action_rows = _receipt_rows(
        [row for row in recoveries if isinstance(row, dict)],
        [row for row in actions if isinstance(row, dict)],
        safe_payload.get("operator") if isinstance(safe_payload.get("operator"), str) else None,
    )

    blockers = []
    if recovery.get("state") == "blocked":
        blockers.extend(deepcopy(recovery.get("blockers") or []))
        blockers.append(_blocker("recovery_blocked", "delivery recovery queue is blocked"))
    blockers.extend(_invalid_action_blockers(action_rows))

    action_status = _status(action_rows, blockers)
    receipt_payload = {
        "schema": CASE_DELIVERY_RECOVERY_ACTION_RECEIPT_SCHEMA,
        "version": VERSION,
        "case_id": case_id,
        "queue_id": recovery.get("queue_id"),
        "recovery_state": recovery.get("state"),
        "status": action_status,
        "action_count": len(action_rows),
        "completed_count": sum(1 for row in action_rows if row.get("completed") is True),
        "pending_count": sum(1 for row in action_rows if row.get("completed") is not True),
        "blocker_count": len(blockers),
        "actions": action_rows,
    }
    receipt_id = sha256_text(canonical_json(receipt_payload))
    return {
        "schema": CASE_DELIVERY_RECOVERY_ACTION_RECEIPT_RESULT_SCHEMA,
        "version": VERSION,
        "case_id": case_id,
        "queue_id": recovery.get("queue_id"),
        "status": "issued" if action_status != "blocked" else "blocked",
        "receipt": {**receipt_payload, "receipt_id": receipt_id} if action_status != "blocked" else None,
        "receipt_id": receipt_id if action_status != "blocked" else None,
        "recovery": recovery,
        "blockers": blockers,
        "blocker_count": len(blockers),
        "next_action": "continue_delivery" if action_status == "completed" else "complete_recovery_actions",
    }


def build_case_delivery_recovery_action_receipt_from_request(case_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    return build_case_delivery_recovery_action_receipt(case_id, payload)
