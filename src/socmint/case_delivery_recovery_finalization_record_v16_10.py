from __future__ import annotations

from copy import deepcopy
from typing import Any

from .case_delivery_handoff_package_v15_1 import canonical_json
from .case_delivery_handoff_package_v15_1 import sha256_text
from .case_delivery_recovery_closure_audit_package_v16_8 import (
    build_case_delivery_recovery_closure_audit_package,
)
from .case_delivery_recovery_closure_audit_package_verification_v16_9 import (
    verify_case_delivery_recovery_closure_audit_package,
)
from .case_delivery_recovery_v16_3 import build_case_delivery_recovery_from_request


CASE_DELIVERY_RECOVERY_FINALIZATION_RECORD_SCHEMA = (
    "socmint.case_delivery_recovery_finalization_record.v16_10"
)
CASE_DELIVERY_RECOVERY_FINALIZATION_RESULT_SCHEMA = (
    "socmint.case_delivery_recovery_finalization_record.v16_10.result"
)
VERSION = "v16.10.0"


def _blocker(key: str, detail: str) -> dict[str, Any]:
    return {"key": key, "detail": detail}


def _finalization_payload(
    recovery: dict[str, Any],
    receipt: dict[str, Any],
    closure: dict[str, Any],
    audit_package: dict[str, Any],
    audit_verification: dict[str, Any],
    finalizer: str | None,
) -> dict[str, Any]:
    return {
        "schema": CASE_DELIVERY_RECOVERY_FINALIZATION_RECORD_SCHEMA,
        "version": VERSION,
        "case_id": recovery.get("case_id") or audit_package.get("case_id"),
        "queue_id": recovery.get("queue_id") or audit_package.get("queue_id"),
        "receipt_id": receipt.get("receipt_id") or audit_package.get("receipt_id"),
        "closure_id": closure.get("closure_id") or audit_package.get("closure_id"),
        "audit_package_id": audit_package.get("audit_package_id"),
        "audit_verification_status": audit_verification.get("status"),
        "ready_for_delivery_continuation": audit_verification.get("verified") is True,
        "finalized_by": finalizer or "system",
        "finalized": audit_verification.get("verified") is True,
    }


def _finalization_blockers(
    recovery: dict[str, Any],
    receipt: dict[str, Any],
    closure: dict[str, Any],
    audit_package: dict[str, Any],
    audit_verification: dict[str, Any],
) -> list[dict[str, Any]]:
    blockers = []
    if not recovery:
        blockers.append(_blocker("missing_recovery", "recovery artifact is missing"))
    if not receipt:
        blockers.append(_blocker("missing_receipt", "receipt artifact is missing"))
    if not closure:
        blockers.append(_blocker("missing_closure", "closure artifact is missing"))
    if not audit_package:
        blockers.append(_blocker("missing_audit_package", "audit package is missing"))
    if not audit_verification:
        blockers.append(
            _blocker(
                "missing_audit_verification", "audit package verification is missing"
            )
        )
    if audit_verification and audit_verification.get("verified") is not True:
        blockers.extend(deepcopy(audit_verification.get("blockers") or []))
        blockers.append(
            _blocker(
                "audit_verification_blocked", "audit package verification did not pass"
            )
        )
    if (
        recovery
        and audit_package
        and recovery.get("queue_id") != audit_package.get("queue_id")
    ):
        blockers.append(
            _blocker(
                "audit_package_queue_mismatch",
                "audit package queue_id does not match recovery queue_id",
            )
        )
    if (
        receipt
        and audit_package
        and receipt.get("receipt_id") != audit_package.get("receipt_id")
    ):
        blockers.append(
            _blocker(
                "audit_package_receipt_mismatch",
                "audit package receipt_id does not match receipt",
            )
        )
    if (
        closure
        and audit_package
        and closure.get("closure_id") != audit_package.get("closure_id")
    ):
        blockers.append(
            _blocker(
                "audit_package_closure_mismatch",
                "audit package closure_id does not match closure",
            )
        )
    if (
        audit_package
        and audit_verification
        and audit_package.get("audit_package_id")
        != audit_verification.get("audit_package_id")
    ):
        blockers.append(
            _blocker(
                "audit_package_id_mismatch",
                "audit package id does not match verification",
            )
        )
    return blockers


def build_case_delivery_recovery_finalization_record(
    recovery: dict[str, Any],
    receipt: dict[str, Any] | None = None,
    closure: dict[str, Any] | None = None,
    audit_package: dict[str, Any] | None = None,
    audit_verification: dict[str, Any] | None = None,
    *,
    finalizer: str | None = None,
) -> dict[str, Any]:
    safe_recovery = deepcopy(recovery or {})
    safe_receipt = deepcopy(receipt or {})
    safe_closure = deepcopy(closure or {})
    safe_audit_package = deepcopy(audit_package or {})
    safe_audit_verification = deepcopy(audit_verification or {})

    if not safe_audit_package:
        package_result = build_case_delivery_recovery_closure_audit_package(
            safe_recovery,
            safe_receipt,
            safe_closure,
            None,
            package_owner=finalizer,
        )
        safe_audit_package = deepcopy(package_result.get("audit_package") or {})
    if not safe_audit_verification:
        safe_audit_verification = verify_case_delivery_recovery_closure_audit_package(
            safe_audit_package,
            safe_recovery,
            safe_receipt,
            safe_closure,
            None,
        )

    blockers = _finalization_blockers(
        safe_recovery,
        safe_receipt,
        safe_closure,
        safe_audit_package,
        safe_audit_verification,
    )
    if blockers:
        return {
            "schema": CASE_DELIVERY_RECOVERY_FINALIZATION_RESULT_SCHEMA,
            "version": VERSION,
            "case_id": safe_recovery.get("case_id")
            or safe_audit_package.get("case_id"),
            "queue_id": safe_recovery.get("queue_id")
            or safe_audit_package.get("queue_id"),
            "audit_package_id": safe_audit_package.get("audit_package_id"),
            "status": "blocked",
            "finalized": False,
            "ready_for_delivery_continuation": False,
            "finalization": None,
            "audit_verification": safe_audit_verification,
            "blockers": blockers,
            "blocker_count": len(blockers),
        }

    payload = _finalization_payload(
        safe_recovery,
        safe_receipt,
        safe_closure,
        safe_audit_package,
        safe_audit_verification,
        finalizer,
    )
    payload_hash = sha256_text(canonical_json(payload))
    finalization = {
        **payload,
        "payload_sha256": payload_hash,
        "finalization_id": sha256_text(
            canonical_json({**payload, "payload_sha256": payload_hash})
        ),
    }
    return {
        "schema": CASE_DELIVERY_RECOVERY_FINALIZATION_RESULT_SCHEMA,
        "version": VERSION,
        "case_id": finalization.get("case_id"),
        "queue_id": finalization.get("queue_id"),
        "audit_package_id": finalization.get("audit_package_id"),
        "status": "finalized",
        "finalized": True,
        "ready_for_delivery_continuation": True,
        "finalization": finalization,
        "audit_verification": safe_audit_verification,
        "blockers": [],
        "blocker_count": 0,
        "next_action": "continue_delivery",
    }


def build_case_delivery_recovery_finalization_record_from_request(
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
    audit_package = (
        safe_payload.get("audit_package")
        if isinstance(safe_payload.get("audit_package"), dict)
        else None
    )
    audit_verification = (
        safe_payload.get("audit_verification")
        if isinstance(safe_payload.get("audit_verification"), dict)
        else None
    )
    finalizer = (
        safe_payload.get("finalizer")
        if isinstance(safe_payload.get("finalizer"), str)
        else None
    )
    return build_case_delivery_recovery_finalization_record(
        recovery,
        receipt,
        closure,
        audit_package,
        audit_verification,
        finalizer=finalizer,
    )
