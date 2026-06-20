from __future__ import annotations

from copy import deepcopy
from typing import Any

from .case_delivery_handoff_package_v15_1 import canonical_json
from .case_delivery_handoff_package_v15_1 import sha256_text
from .case_delivery_operations_v16_0 import build_case_delivery_operations_from_request


CASE_DELIVERY_ATTEMPT_LEDGER_SCHEMA = "socmint.case_delivery_attempt_ledger.v16_1"
VERSION = "v16.1.0"
RETRYABLE_STATUSES = {"failed", "exception", "timeout"}
SUCCESS_STATUSES = {"succeeded", "delivered"}


def _blocker(key: str, detail: str) -> dict[str, Any]:
    return {"key": key, "detail": detail}


def _attempt_rows(attempts: list[Any]) -> list[dict[str, Any]]:
    rows = []
    for index, attempt in enumerate(attempts, start=1):
        if not isinstance(attempt, dict):
            continue
        status = attempt.get("status") or "pending"
        payload = {
            "sequence": index,
            "channel": attempt.get("channel") or "unspecified",
            "status": status,
            "operator": attempt.get("operator") or "unassigned",
            "detail": attempt.get("detail") or "",
            "retryable": status in RETRYABLE_STATUSES
            and attempt.get("retryable", True) is not False,
        }
        rows.append(
            {
                **payload,
                "attempt_id": sha256_text(canonical_json(payload)),
            }
        )
    return rows


def _ledger_state(
    operations: dict[str, Any],
    attempts: list[dict[str, Any]],
) -> tuple[str, list[dict[str, Any]], bool]:
    blockers = []
    if operations.get("dispatchable") is not True:
        blockers.extend(deepcopy(operations.get("blockers") or []))
        blockers.append(
            _blocker(
                "operations_blocked", "delivery operations snapshot is not dispatchable"
            )
        )
    if blockers:
        return "blocked", blockers, False

    if any(attempt.get("status") in SUCCESS_STATUSES for attempt in attempts):
        return "delivered", blockers, False
    if any(attempt.get("retryable") is True for attempt in attempts):
        return "retry_ready", blockers, True
    if attempts:
        return "attempt_recorded", blockers, False
    return "ready_for_attempt", blockers, True


def build_case_delivery_attempt_ledger(
    case_id: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    safe_payload = deepcopy(payload or {})
    operations = (
        deepcopy(safe_payload.get("operations"))
        if isinstance(safe_payload.get("operations"), dict)
        else build_case_delivery_operations_from_request(case_id, safe_payload)
    )
    attempts = _attempt_rows(
        safe_payload.get("attempts")
        if isinstance(safe_payload.get("attempts"), list)
        else []
    )
    state, blockers, retry_eligible = _ledger_state(operations, attempts)
    latest_attempt = attempts[-1] if attempts else {}
    success_count = sum(
        1 for attempt in attempts if attempt.get("status") in SUCCESS_STATUSES
    )
    failure_count = sum(
        1 for attempt in attempts if attempt.get("status") in RETRYABLE_STATUSES
    )
    payload_core = {
        "schema": CASE_DELIVERY_ATTEMPT_LEDGER_SCHEMA,
        "version": VERSION,
        "case_id": case_id,
        "operation_id": operations.get("operation_id"),
        "execution_id": operations.get("execution_id"),
        "state": state,
        "attempt_count": len(attempts),
        "success_count": success_count,
        "failure_count": failure_count,
        "latest_attempt_status": latest_attempt.get("status"),
        "retry_eligible": retry_eligible,
        "blocker_count": len(blockers),
    }
    result = {
        **payload_core,
        "operations": operations,
        "attempts": attempts,
        "blockers": blockers,
        "next_action": "record_delivery_attempt"
        if retry_eligible
        else "review_delivery_attempts",
    }
    return {
        **result,
        "ledger_id": sha256_text(canonical_json(result)),
    }


def build_case_delivery_attempt_ledger_from_request(
    case_id: str, payload: dict[str, Any]
) -> dict[str, Any]:
    return build_case_delivery_attempt_ledger(case_id, payload)
