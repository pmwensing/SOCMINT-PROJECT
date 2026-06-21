from __future__ import annotations

from copy import deepcopy
from typing import Any

from .case_delivery_handoff_package_v15_1 import canonical_json
from .case_delivery_handoff_package_v15_1 import sha256_text
from .case_delivery_recovery_action_receipt_v16_4 import (
    build_case_delivery_recovery_action_receipt,
)
from .case_delivery_recovery_v16_3 import build_case_delivery_recovery_from_request


CASE_DELIVERY_RECOVERY_ACTION_RECEIPT_VERIFICATION_SCHEMA = (
    "socmint.case_delivery_recovery_action_receipt_verification.v16_5"
)
VERSION = "v16.5.0"
VALID_DECISIONS = {"retry", "remediate", "escalate", "hold"}
VALID_ACTION_STATUSES = {
    "completed",
    "confirmed",
    "resolved",
    "acknowledged",
    "pending",
    "in_progress",
    "queued",
    "deferred",
}
COMPLETED_STATUSES = {"completed", "confirmed", "resolved", "acknowledged"}


RECEIPT_PAYLOAD_FIELDS = (
    "schema",
    "version",
    "case_id",
    "queue_id",
    "recovery_state",
    "status",
    "action_count",
    "completed_count",
    "pending_count",
    "blocker_count",
    "actions",
)

ACTION_RECEIPT_FIELDS = (
    "sequence",
    "recovery_id",
    "exception_id",
    "attempt_id",
    "category",
    "decision",
    "queue_state",
    "recommendation",
    "operator",
    "action_status",
    "completed",
    "detail",
)


def _blocker(key: str, detail: str) -> dict[str, Any]:
    return {"key": key, "detail": detail}


def _receipt_payload(receipt: dict[str, Any]) -> dict[str, Any]:
    return {field: receipt.get(field) for field in RECEIPT_PAYLOAD_FIELDS}


def _action_payload(action: dict[str, Any]) -> dict[str, Any]:
    return {field: action.get(field) for field in ACTION_RECEIPT_FIELDS}


def _recovery_index(recovery: dict[str, Any]) -> dict[str, dict[str, Any]]:
    queue = (
        recovery.get("operator_recovery_queue")
        if isinstance(recovery.get("operator_recovery_queue"), list)
        else []
    )
    return {
        row.get("recovery_id"): row
        for row in queue
        if isinstance(row, dict) and row.get("recovery_id")
    }


def _action_blockers(
    action: dict[str, Any], recovery_by_id: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    blockers = []
    recovery_id = action.get("recovery_id")
    recovery = recovery_by_id.get(recovery_id)
    if not recovery:
        blockers.append(
            _blocker(
                "recovery_id_missing",
                f"action recovery_id {recovery_id} is not present in the recovery queue",
            )
        )
        return blockers

    expected_action_receipt_id = sha256_text(canonical_json(_action_payload(action)))
    if action.get("action_receipt_id") != expected_action_receipt_id:
        blockers.append(
            _blocker(
                "action_receipt_id_mismatch",
                f"action receipt id for recovery {recovery_id} is invalid",
            )
        )

    for field in (
        "exception_id",
        "attempt_id",
        "category",
        "decision",
        "queue_state",
        "recommendation",
    ):
        if action.get(field) != recovery.get(field):
            blockers.append(
                _blocker(
                    f"{field}_mismatch",
                    f"action {field} does not match recovery queue item",
                )
            )

    if action.get("decision") not in VALID_DECISIONS:
        blockers.append(
            _blocker("invalid_recovery_decision", "action decision is not supported")
        )
    if action.get("action_status") not in VALID_ACTION_STATUSES:
        blockers.append(
            _blocker("invalid_action_status", "action status is not supported")
        )
    if action.get("completed") != (action.get("action_status") in COMPLETED_STATUSES):
        blockers.append(
            _blocker(
                "completed_flag_mismatch",
                "action completed flag does not match action status",
            )
        )
    return blockers


def verify_case_delivery_recovery_action_receipt(
    receipt: dict[str, Any] | None,
    recovery: dict[str, Any],
) -> dict[str, Any]:
    safe_receipt = deepcopy(receipt or {})
    safe_recovery = deepcopy(recovery or {})
    blockers = []

    if not safe_receipt:
        blockers.append(
            _blocker("missing_receipt", "recovery action receipt is missing")
        )
    if safe_recovery.get("state") == "blocked":
        blockers.extend(deepcopy(safe_recovery.get("blockers") or []))
        blockers.append(
            _blocker("recovery_blocked", "delivery recovery queue is blocked")
        )

    expected_receipt_id = (
        sha256_text(canonical_json(_receipt_payload(safe_receipt)))
        if safe_receipt
        else None
    )
    if safe_receipt and safe_receipt.get("receipt_id") != expected_receipt_id:
        blockers.append(
            _blocker(
                "receipt_id_mismatch",
                "receipt id does not match canonical receipt payload",
            )
        )

    if safe_receipt and safe_receipt.get("queue_id") != safe_recovery.get("queue_id"):
        blockers.append(
            _blocker(
                "queue_id_mismatch", "receipt queue_id does not match recovery queue"
            )
        )
    if safe_receipt and safe_receipt.get("case_id") != safe_recovery.get("case_id"):
        blockers.append(
            _blocker(
                "case_id_mismatch", "receipt case_id does not match recovery queue"
            )
        )
    if safe_receipt and safe_receipt.get("recovery_state") != safe_recovery.get(
        "state"
    ):
        blockers.append(
            _blocker(
                "recovery_state_mismatch",
                "receipt recovery_state does not match recovery queue",
            )
        )

    actions = (
        safe_receipt.get("actions")
        if isinstance(safe_receipt.get("actions"), list)
        else []
    )
    recovery_by_id = _recovery_index(safe_recovery)
    for action in [row for row in actions if isinstance(row, dict)]:
        blockers.extend(_action_blockers(action, recovery_by_id))

    if safe_receipt:
        completed_count = sum(
            1
            for action in actions
            if isinstance(action, dict) and action.get("completed") is True
        )
        pending_count = sum(
            1
            for action in actions
            if isinstance(action, dict) and action.get("completed") is not True
        )
        if safe_receipt.get("action_count") != len(actions):
            blockers.append(
                _blocker(
                    "action_count_mismatch",
                    "receipt action_count does not match actions",
                )
            )
        if safe_receipt.get("completed_count") != completed_count:
            blockers.append(
                _blocker(
                    "completed_count_mismatch",
                    "receipt completed_count does not match actions",
                )
            )
        if safe_receipt.get("pending_count") != pending_count:
            blockers.append(
                _blocker(
                    "pending_count_mismatch",
                    "receipt pending_count does not match actions",
                )
            )
        if safe_receipt.get("blocker_count") not in (0, len(blockers)):
            blockers.append(
                _blocker(
                    "blocker_count_mismatch", "receipt blocker_count is inconsistent"
                )
            )

    status = "verified" if not blockers else "blocked"
    return {
        "schema": CASE_DELIVERY_RECOVERY_ACTION_RECEIPT_VERIFICATION_SCHEMA,
        "version": VERSION,
        "case_id": safe_receipt.get("case_id") or safe_recovery.get("case_id"),
        "queue_id": safe_receipt.get("queue_id") or safe_recovery.get("queue_id"),
        "receipt_id": safe_receipt.get("receipt_id"),
        "status": status,
        "verified": not blockers,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "recovery": safe_recovery,
    }


def verify_case_delivery_recovery_action_receipt_from_request(
    case_id: str, payload: dict[str, Any]
) -> dict[str, Any]:
    safe_payload = deepcopy(payload or {})
    recovery = (
        safe_payload.get("recovery")
        if isinstance(safe_payload.get("recovery"), dict)
        else None
    )
    if recovery is None:
        recovery = build_case_delivery_recovery_from_request(case_id, safe_payload)
    receipt = (
        safe_payload.get("receipt")
        if isinstance(safe_payload.get("receipt"), dict)
        else None
    )
    if receipt is None:
        receipt_result = build_case_delivery_recovery_action_receipt(
            case_id, {**safe_payload, "recovery": recovery}
        )
        receipt = (
            receipt_result.get("receipt")
            if isinstance(receipt_result.get("receipt"), dict)
            else None
        )
    return verify_case_delivery_recovery_action_receipt(receipt, recovery)
