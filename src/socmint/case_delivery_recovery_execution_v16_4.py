from __future__ import annotations

from copy import deepcopy
from typing import Any

from .case_delivery_handoff_package_v15_1 import canonical_json
from .case_delivery_handoff_package_v15_1 import sha256_text
from .case_delivery_recovery_v16_3 import build_case_delivery_recovery_from_request


CASE_DELIVERY_RECOVERY_EXECUTION_SCHEMA = "socmint.case_delivery_recovery_execution.v16_4"
VERSION = "v16.4.0"

ALLOWED_EXECUTION_STATES = {
    "retried",
    "held",
    "escalated",
    "remediated",
    "completed",
    "failed",
}

DEFAULT_STATE_BY_DECISION = {
    "retry": "retried",
    "hold": "held",
    "escalate": "escalated",
    "remediate": "remediated",
}

SUCCESS_STATES = {"retried", "held", "escalated", "remediated", "completed"}


def _blocker(key: str, detail: str) -> dict[str, Any]:
    return {"key": key, "detail": detail}


def _execution_inputs(payload: dict[str, Any]) -> list[dict[str, Any]]:
    values = payload.get("executions")
    if isinstance(values, list):
        return [item for item in values if isinstance(item, dict)]
    value = payload.get("execution")
    if isinstance(value, dict):
        return [value]
    return []


def _input_for_item(inputs: list[dict[str, Any]], item: dict[str, Any]) -> dict[str, Any]:
    recovery_id = item.get("recovery_id")
    for execution in inputs:
        if execution.get("recovery_id") == recovery_id:
            return execution
    return {}


def _execution_state(item: dict[str, Any], execution_input: dict[str, Any]) -> str:
    requested_state = execution_input.get("state") or execution_input.get("status")
    if requested_state in ALLOWED_EXECUTION_STATES:
        return str(requested_state)
    return DEFAULT_STATE_BY_DECISION.get(str(item.get("decision") or ""), "held")


def _execution_rows(queue: list[dict[str, Any]], execution_inputs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for sequence, item in enumerate(queue, start=1):
        if not isinstance(item, dict):
            continue
        execution_input = _input_for_item(execution_inputs, item)
        state = _execution_state(item, execution_input)
        payload = {
            "recovery_id": item.get("recovery_id"),
            "exception_id": item.get("exception_id"),
            "attempt_id": item.get("attempt_id"),
            "sequence": sequence,
            "decision": item.get("decision"),
            "execution_state": state,
            "operator": execution_input.get("operator") or execution_input.get("executed_by") or "operator",
            "detail": execution_input.get("detail") or execution_input.get("notes") or item.get("recommendation"),
            "successful": state in SUCCESS_STATES,
        }
        rows.append({**payload, "execution_id": sha256_text(canonical_json(payload))})
    return rows


def _summary_state(recovery: dict[str, Any], executions: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    blockers = []
    if recovery.get("state") == "blocked":
        blockers.extend(deepcopy(recovery.get("blockers") or []))
        blockers.append(_blocker("recovery_queue_blocked", "delivery recovery queue is blocked"))
        return "blocked", blockers
    if not executions:
        return "clear", blockers
    if any(row.get("execution_state") == "failed" for row in executions):
        return "failed", blockers
    if all(row.get("successful") is True for row in executions):
        return "completed", blockers
    return "in_progress", blockers


def _next_action(state: str) -> str:
    if state == "clear":
        return "continue_delivery"
    if state == "completed":
        return "continue_delivery_after_recovery"
    if state == "failed":
        return "review_failed_recovery_execution"
    if state == "blocked":
        return "resolve_execution_blockers"
    return "continue_recovery_execution"


def build_case_delivery_recovery_execution(
    case_id: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    safe_payload = deepcopy(payload or {})
    recovery = (
        deepcopy(safe_payload.get("recovery"))
        if isinstance(safe_payload.get("recovery"), dict)
        else build_case_delivery_recovery_from_request(case_id, safe_payload)
    )
    queue = recovery.get("operator_recovery_queue") if isinstance(recovery.get("operator_recovery_queue"), list) else []
    executions = _execution_rows([item for item in queue if isinstance(item, dict)], _execution_inputs(safe_payload))
    state, blockers = _summary_state(recovery, executions)
    payload_core = {
        "schema": CASE_DELIVERY_RECOVERY_EXECUTION_SCHEMA,
        "version": VERSION,
        "case_id": case_id,
        "queue_id": recovery.get("queue_id"),
        "state": state,
        "execution_count": len(executions),
        "retried_count": sum(1 for row in executions if row.get("execution_state") == "retried"),
        "held_count": sum(1 for row in executions if row.get("execution_state") == "held"),
        "escalated_count": sum(1 for row in executions if row.get("execution_state") == "escalated"),
        "remediated_count": sum(1 for row in executions if row.get("execution_state") == "remediated"),
        "completed_count": sum(1 for row in executions if row.get("execution_state") == "completed"),
        "failed_count": sum(1 for row in executions if row.get("execution_state") == "failed"),
        "blocker_count": len(blockers),
    }
    return {
        **payload_core,
        "execution_record_id": sha256_text(canonical_json(payload_core)),
        "recovery": recovery,
        "executions": executions,
        "result_summary": {
            "state": state,
            "successful_count": sum(1 for row in executions if row.get("successful") is True),
            "failed_count": payload_core["failed_count"],
            "next_action": _next_action(state),
        },
        "blockers": blockers,
        "next_action": _next_action(state),
    }


def build_case_delivery_recovery_execution_from_request(case_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    return build_case_delivery_recovery_execution(case_id, payload)
