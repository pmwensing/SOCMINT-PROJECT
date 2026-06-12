from __future__ import annotations

from copy import deepcopy
from typing import Any

from .case_delivery_handoff_package_v15_1 import canonical_json
from .case_delivery_handoff_package_v15_1 import sha256_text
from .case_delivery_recovery_action_receipt_v16_4 import build_case_delivery_recovery_action_receipt
from .case_delivery_recovery_action_receipt_verification_v16_5 import (
    verify_case_delivery_recovery_action_receipt,
)
from .case_delivery_recovery_v16_3 import build_case_delivery_recovery_from_request


CASE_DELIVERY_RECOVERY_CLOSURE_RECORD_SCHEMA = "socmint.case_delivery_recovery_closure_record.v16_6"
CASE_DELIVERY_RECOVERY_CLOSURE_RESULT_SCHEMA = "socmint.case_delivery_recovery_closure_record.v16_6.result"
VERSION = "v16.6.0"

CLOSABLE_RECEIPT_STATUSES = {"completed", "no_action_required"}


def _blocker(key: str, detail: str) -> dict[str, Any]:
    return {"key": key, "detail": detail}


def _closure_payload(
    recovery: dict[str, Any],
    receipt: dict[str, Any],
    verification: dict[str, Any],
    closer: str | None,
) -> dict[str, Any]:
    return {
        "schema": CASE_DELIVERY_RECOVERY_CLOSURE_RECORD_SCHEMA,
        "version": VERSION,
        "case_id": recovery.get("case_id") or receipt.get("case_id"),
        "queue_id": recovery.get("queue_id") or receipt.get("queue_id"),
        "receipt_id": receipt.get("receipt_id"),
        "verification_status": verification.get("status"),
        "recovery_state": recovery.get("state"),
        "receipt_status": receipt.get("status"),
        "action_count": receipt.get("action_count", 0),
        "completed_count": receipt.get("completed_count", 0),
        "pending_count": receipt.get("pending_count", 0),
        "closed_by": closer or "system",
        "closed": verification.get("verified") is True and receipt.get("status") in CLOSABLE_RECEIPT_STATUSES,
    }


def _closure_blockers(receipt: dict[str, Any], verification: dict[str, Any]) -> list[dict[str, Any]]:
    blockers = []
    if not verification.get("verified"):
        blockers.extend(deepcopy(verification.get("blockers") or []))
        blockers.append(_blocker("receipt_verification_blocked", "recovery action receipt verification did not pass"))
    if receipt and receipt.get("status") not in CLOSABLE_RECEIPT_STATUSES:
        blockers.append(_blocker("receipt_not_complete", "recovery action receipt is not complete"))
    return blockers


def build_case_delivery_recovery_closure_record(
    recovery: dict[str, Any],
    receipt: dict[str, Any] | None = None,
    *,
    closer: str | None = None,
) -> dict[str, Any]:
    safe_recovery = deepcopy(recovery or {})
    safe_receipt = deepcopy(receipt or {})
    if not safe_receipt:
        receipt_result = build_case_delivery_recovery_action_receipt(
            safe_recovery.get("case_id") or "case-delivery-preview",
            {"recovery": safe_recovery, "operator": closer},
        )
        safe_receipt = deepcopy(receipt_result.get("receipt") or {})

    verification = verify_case_delivery_recovery_action_receipt(safe_receipt, safe_recovery)
    blockers = _closure_blockers(safe_receipt, verification)
    if blockers:
        return {
            "schema": CASE_DELIVERY_RECOVERY_CLOSURE_RESULT_SCHEMA,
            "version": VERSION,
            "case_id": safe_recovery.get("case_id") or safe_receipt.get("case_id"),
            "queue_id": safe_recovery.get("queue_id") or safe_receipt.get("queue_id"),
            "receipt_id": safe_receipt.get("receipt_id"),
            "status": "blocked",
            "closed": False,
            "closure": None,
            "receipt_verification": verification,
            "blockers": blockers,
            "blocker_count": len(blockers),
        }

    payload = _closure_payload(safe_recovery, safe_receipt, verification, closer)
    payload_hash = sha256_text(canonical_json(payload))
    closure = {
        **payload,
        "payload_sha256": payload_hash,
        "closure_id": sha256_text(canonical_json({**payload, "payload_sha256": payload_hash})),
    }
    return {
        "schema": CASE_DELIVERY_RECOVERY_CLOSURE_RESULT_SCHEMA,
        "version": VERSION,
        "case_id": safe_recovery.get("case_id") or safe_receipt.get("case_id"),
        "queue_id": safe_recovery.get("queue_id") or safe_receipt.get("queue_id"),
        "receipt_id": safe_receipt.get("receipt_id"),
        "status": "closed",
        "closed": True,
        "closure": closure,
        "receipt_verification": verification,
        "blockers": [],
        "blocker_count": 0,
    }


def build_case_delivery_recovery_closure_record_from_request(case_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    safe_payload = deepcopy(payload or {})
    recovery = safe_payload.get("recovery") if isinstance(safe_payload.get("recovery"), dict) else None
    if recovery is None:
        recovery = build_case_delivery_recovery_from_request(case_id, safe_payload)
    receipt = safe_payload.get("receipt") if isinstance(safe_payload.get("receipt"), dict) else None
    closer = safe_payload.get("closer") if isinstance(safe_payload.get("closer"), str) else None
    return build_case_delivery_recovery_closure_record(recovery, receipt, closer=closer)
