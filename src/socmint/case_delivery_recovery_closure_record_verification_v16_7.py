from __future__ import annotations

from copy import deepcopy
from typing import Any

from .case_delivery_handoff_package_v15_1 import canonical_json
from .case_delivery_handoff_package_v15_1 import sha256_text
from .case_delivery_recovery_action_receipt_verification_v16_5 import (
    verify_case_delivery_recovery_action_receipt,
)
from .case_delivery_recovery_closure_record_v16_6 import CLOSABLE_RECEIPT_STATUSES
from .case_delivery_recovery_closure_record_v16_6 import (
    build_case_delivery_recovery_closure_record,
)
from .case_delivery_recovery_v16_3 import build_case_delivery_recovery_from_request


CASE_DELIVERY_RECOVERY_CLOSURE_RECORD_VERIFICATION_SCHEMA = (
    "socmint.case_delivery_recovery_closure_record_verification.v16_7"
)
VERSION = "v16.7.0"

CLOSURE_PAYLOAD_FIELDS = (
    "schema",
    "version",
    "case_id",
    "queue_id",
    "receipt_id",
    "verification_status",
    "recovery_state",
    "receipt_status",
    "action_count",
    "completed_count",
    "pending_count",
    "closed_by",
    "closed",
)


def _blocker(key: str, detail: str) -> dict[str, Any]:
    return {"key": key, "detail": detail}


def _closure_payload(closure: dict[str, Any]) -> dict[str, Any]:
    return {field: closure.get(field) for field in CLOSURE_PAYLOAD_FIELDS}


def verify_case_delivery_recovery_closure_record(
    closure: dict[str, Any] | None,
    recovery: dict[str, Any],
    receipt: dict[str, Any] | None,
) -> dict[str, Any]:
    safe_closure = deepcopy(closure or {})
    safe_recovery = deepcopy(recovery or {})
    safe_receipt = deepcopy(receipt or {})
    receipt_verification = verify_case_delivery_recovery_action_receipt(
        safe_receipt, safe_recovery
    )
    blockers = []

    if not safe_closure:
        blockers.append(_blocker("missing_closure", "closure record is missing"))
    if not receipt_verification.get("verified"):
        blockers.extend(deepcopy(receipt_verification.get("blockers") or []))
        blockers.append(
            _blocker(
                "receipt_verification_blocked", "receipt verification did not pass"
            )
        )

    expected_payload_hash = (
        sha256_text(canonical_json(_closure_payload(safe_closure)))
        if safe_closure
        else None
    )
    if safe_closure and safe_closure.get("payload_sha256") != expected_payload_hash:
        blockers.append(
            _blocker(
                "payload_hash_mismatch",
                "closure payload hash does not match closure fields",
            )
        )

    expected_closure_id = (
        sha256_text(
            canonical_json(
                {
                    **_closure_payload(safe_closure),
                    "payload_sha256": safe_closure.get("payload_sha256"),
                }
            )
        )
        if safe_closure
        else None
    )
    if safe_closure and safe_closure.get("closure_id") != expected_closure_id:
        blockers.append(
            _blocker(
                "closure_id_mismatch",
                "closure id does not match canonical closure payload",
            )
        )

    if safe_closure and safe_closure.get("queue_id") != safe_recovery.get("queue_id"):
        blockers.append(
            _blocker("queue_id_mismatch", "closure queue_id does not match queue")
        )
    if safe_closure and safe_closure.get("case_id") != safe_recovery.get("case_id"):
        blockers.append(
            _blocker("case_id_mismatch", "closure case_id does not match queue")
        )
    if safe_closure and safe_closure.get("receipt_id") != safe_receipt.get(
        "receipt_id"
    ):
        blockers.append(
            _blocker("receipt_id_mismatch", "closure receipt_id does not match receipt")
        )
    if safe_closure and safe_closure.get(
        "verification_status"
    ) != receipt_verification.get("status"):
        blockers.append(
            _blocker(
                "verification_status_mismatch",
                "closure verification status does not match receipt verification",
            )
        )
    if safe_closure and safe_closure.get("recovery_state") != safe_recovery.get(
        "state"
    ):
        blockers.append(
            _blocker(
                "recovery_state_mismatch", "closure recovery_state does not match queue"
            )
        )
    if safe_closure and safe_closure.get("receipt_status") != safe_receipt.get(
        "status"
    ):
        blockers.append(
            _blocker(
                "receipt_status_mismatch",
                "closure receipt_status does not match receipt",
            )
        )
    if (
        safe_closure
        and safe_closure.get("receipt_status") not in CLOSABLE_RECEIPT_STATUSES
    ):
        blockers.append(
            _blocker("receipt_not_complete", "closure receipt status is not closable")
        )
    if safe_closure and safe_closure.get("closed") is not True:
        blockers.append(
            _blocker("closure_not_closed", "closure closed flag is not true")
        )

    for field in ("action_count", "completed_count", "pending_count"):
        if safe_closure and safe_closure.get(field) != safe_receipt.get(field, 0):
            blockers.append(
                _blocker(f"{field}_mismatch", f"closure {field} does not match receipt")
            )

    status = "verified" if not blockers else "blocked"
    return {
        "schema": CASE_DELIVERY_RECOVERY_CLOSURE_RECORD_VERIFICATION_SCHEMA,
        "version": VERSION,
        "case_id": safe_closure.get("case_id") or safe_recovery.get("case_id"),
        "queue_id": safe_closure.get("queue_id") or safe_recovery.get("queue_id"),
        "receipt_id": safe_closure.get("receipt_id") or safe_receipt.get("receipt_id"),
        "closure_id": safe_closure.get("closure_id"),
        "status": status,
        "verified": not blockers,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "receipt_verification": receipt_verification,
    }


def verify_case_delivery_recovery_closure_record_from_request(
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
    closure = (
        safe_payload.get("closure")
        if isinstance(safe_payload.get("closure"), dict)
        else None
    )
    if closure is None:
        closure_result = build_case_delivery_recovery_closure_record(
            recovery, receipt, closer=safe_payload.get("closer")
        )
        closure = (
            closure_result.get("closure")
            if isinstance(closure_result.get("closure"), dict)
            else None
        )
    return verify_case_delivery_recovery_closure_record(closure, recovery, receipt)
