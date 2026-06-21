from __future__ import annotations

from copy import deepcopy
from typing import Any

from .case_delivery_handoff_package_v15_1 import canonical_json
from .case_delivery_handoff_package_v15_1 import sha256_text
from .case_delivery_recovery_finalization_record_v16_10 import (
    build_case_delivery_recovery_finalization_record,
)
from .case_delivery_recovery_finalization_record_verification_v16_11 import (
    verify_case_delivery_recovery_finalization_record,
)
from .case_delivery_recovery_v16_3 import build_case_delivery_recovery_from_request


CASE_DELIVERY_RECOVERY_CONTINUATION_GATE_SCHEMA = (
    "socmint.case_delivery_recovery_continuation_gate.v16_12"
)
CASE_DELIVERY_RECOVERY_CONTINUATION_GATE_RESULT_SCHEMA = (
    "socmint.case_delivery_recovery_continuation_gate.v16_12.result"
)
VERSION = "v16.12.0"
NEXT_ACTION = "resume_delivery_operations"


def _blocker(key: str, detail: str) -> dict[str, Any]:
    return {"key": key, "detail": detail}


def _gate_payload(
    recovery: dict[str, Any],
    finalization: dict[str, Any],
    finalization_verification: dict[str, Any],
    gate_operator: str | None,
) -> dict[str, Any]:
    return {
        "schema": CASE_DELIVERY_RECOVERY_CONTINUATION_GATE_SCHEMA,
        "version": VERSION,
        "case_id": recovery.get("case_id") or finalization.get("case_id"),
        "queue_id": recovery.get("queue_id") or finalization.get("queue_id"),
        "finalization_id": finalization.get("finalization_id"),
        "audit_package_id": finalization.get("audit_package_id"),
        "finalization_verification_status": finalization_verification.get("status"),
        "finalization_verified": finalization_verification.get("verified") is True,
        "ready_for_delivery_continuation": finalization_verification.get(
            "ready_for_delivery_continuation"
        )
        is True,
        "gate_operator": gate_operator or "system",
        "next_action": NEXT_ACTION,
        "gate_open": finalization_verification.get("verified") is True
        and finalization_verification.get("ready_for_delivery_continuation") is True,
    }


def _gate_blockers(
    recovery: dict[str, Any],
    finalization: dict[str, Any],
    finalization_verification: dict[str, Any],
) -> list[dict[str, Any]]:
    blockers = []
    if not recovery:
        blockers.append(_blocker("missing_recovery", "recovery artifact is missing"))
    if not finalization:
        blockers.append(
            _blocker("missing_finalization", "finalization artifact is missing")
        )
    if not finalization_verification:
        blockers.append(
            _blocker(
                "missing_finalization_verification",
                "finalization verification artifact is missing",
            )
        )
    if (
        finalization_verification
        and finalization_verification.get("verified") is not True
    ):
        blockers.extend(deepcopy(finalization_verification.get("blockers") or []))
        blockers.append(
            _blocker(
                "finalization_verification_blocked",
                "finalization verification did not pass",
            )
        )
    if (
        finalization_verification
        and finalization_verification.get("ready_for_delivery_continuation") is not True
    ):
        blockers.append(
            _blocker(
                "not_ready_for_delivery_continuation",
                "finalization verification is not ready for delivery continuation",
            )
        )
    if (
        recovery
        and finalization
        and recovery.get("queue_id") != finalization.get("queue_id")
    ):
        blockers.append(
            _blocker(
                "finalization_queue_mismatch",
                "finalization queue_id does not match recovery queue_id",
            )
        )
    if (
        finalization
        and finalization_verification
        and finalization.get("finalization_id")
        != finalization_verification.get("finalization_id")
    ):
        blockers.append(
            _blocker(
                "finalization_id_mismatch",
                "finalization id does not match verification",
            )
        )
    if (
        finalization
        and finalization_verification
        and finalization.get("audit_package_id")
        != finalization_verification.get("audit_package_id")
    ):
        blockers.append(
            _blocker(
                "audit_package_id_mismatch",
                "audit package id does not match verification",
            )
        )
    return blockers


def build_case_delivery_recovery_continuation_gate(
    recovery: dict[str, Any],
    receipt: dict[str, Any] | None = None,
    closure: dict[str, Any] | None = None,
    audit_package: dict[str, Any] | None = None,
    audit_verification: dict[str, Any] | None = None,
    finalization: dict[str, Any] | None = None,
    finalization_verification: dict[str, Any] | None = None,
    *,
    gate_operator: str | None = None,
) -> dict[str, Any]:
    safe_recovery = deepcopy(recovery or {})
    safe_receipt = deepcopy(receipt or {})
    safe_closure = deepcopy(closure or {})
    safe_audit_package = deepcopy(audit_package or {})
    safe_audit_verification = deepcopy(audit_verification or {})
    safe_finalization = deepcopy(finalization or {})
    safe_finalization_verification = deepcopy(finalization_verification or {})

    if not safe_finalization:
        finalization_result = build_case_delivery_recovery_finalization_record(
            safe_recovery,
            safe_receipt,
            safe_closure,
            safe_audit_package,
            safe_audit_verification,
            finalizer=gate_operator,
        )
        safe_finalization = deepcopy(finalization_result.get("finalization") or {})
    if not safe_finalization_verification:
        safe_finalization_verification = (
            verify_case_delivery_recovery_finalization_record(
                safe_finalization,
                safe_recovery,
                safe_receipt,
                safe_closure,
                safe_audit_package,
                safe_audit_verification,
            )
        )

    blockers = _gate_blockers(
        safe_recovery, safe_finalization, safe_finalization_verification
    )
    if blockers:
        return {
            "schema": CASE_DELIVERY_RECOVERY_CONTINUATION_GATE_RESULT_SCHEMA,
            "version": VERSION,
            "case_id": safe_recovery.get("case_id") or safe_finalization.get("case_id"),
            "queue_id": safe_recovery.get("queue_id")
            or safe_finalization.get("queue_id"),
            "finalization_id": safe_finalization.get("finalization_id"),
            "status": "blocked",
            "gate_open": False,
            "ready_for_delivery_continuation": False,
            "continuation_gate": None,
            "finalization_verification": safe_finalization_verification,
            "blockers": blockers,
            "blocker_count": len(blockers),
            "next_action": "resolve_recovery_finalization",
        }

    payload = _gate_payload(
        safe_recovery, safe_finalization, safe_finalization_verification, gate_operator
    )
    payload_hash = sha256_text(canonical_json(payload))
    continuation_gate = {
        **payload,
        "payload_sha256": payload_hash,
        "continuation_gate_id": sha256_text(
            canonical_json({**payload, "payload_sha256": payload_hash})
        ),
    }
    return {
        "schema": CASE_DELIVERY_RECOVERY_CONTINUATION_GATE_RESULT_SCHEMA,
        "version": VERSION,
        "case_id": continuation_gate.get("case_id"),
        "queue_id": continuation_gate.get("queue_id"),
        "finalization_id": continuation_gate.get("finalization_id"),
        "status": "open",
        "gate_open": True,
        "ready_for_delivery_continuation": True,
        "continuation_gate": continuation_gate,
        "finalization_verification": safe_finalization_verification,
        "blockers": [],
        "blocker_count": 0,
        "next_action": NEXT_ACTION,
    }


def build_case_delivery_recovery_continuation_gate_from_request(
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
    finalization = (
        safe_payload.get("finalization")
        if isinstance(safe_payload.get("finalization"), dict)
        else None
    )
    finalization_verification = (
        safe_payload.get("finalization_verification")
        if isinstance(safe_payload.get("finalization_verification"), dict)
        else None
    )
    gate_operator = (
        safe_payload.get("gate_operator")
        if isinstance(safe_payload.get("gate_operator"), str)
        else None
    )
    return build_case_delivery_recovery_continuation_gate(
        recovery,
        receipt,
        closure,
        audit_package,
        audit_verification,
        finalization,
        finalization_verification,
        gate_operator=gate_operator,
    )
