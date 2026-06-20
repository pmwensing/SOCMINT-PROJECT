from __future__ import annotations

from copy import deepcopy
from typing import Any

from .case_delivery_handoff_package_v15_1 import canonical_json
from .case_delivery_handoff_package_v15_1 import sha256_text
from .case_delivery_recovery_continuation_gate_v16_12 import (
    build_case_delivery_recovery_continuation_gate,
)
from .case_delivery_recovery_continuation_gate_verification_v16_13 import (
    verify_case_delivery_recovery_continuation_gate,
)
from .case_delivery_recovery_v16_3 import build_case_delivery_recovery_from_request


CASE_DELIVERY_RECOVERY_RESUME_OPERATIONS_SNAPSHOT_SCHEMA = (
    "socmint.case_delivery_recovery_resume_operations_snapshot.v16_14"
)
CASE_DELIVERY_RECOVERY_RESUME_OPERATIONS_RESULT_SCHEMA = (
    "socmint.case_delivery_recovery_resume_operations_snapshot.v16_14.result"
)
VERSION = "v16.14.0"
NEXT_ACTION = "execute_delivery_operations"


def _blocker(key: str, detail: str) -> dict[str, Any]:
    return {"key": key, "detail": detail}


def _resume_payload(
    recovery: dict[str, Any],
    continuation_gate: dict[str, Any],
    continuation_gate_verification: dict[str, Any],
    resume_operator: str | None,
) -> dict[str, Any]:
    return {
        "schema": CASE_DELIVERY_RECOVERY_RESUME_OPERATIONS_SNAPSHOT_SCHEMA,
        "version": VERSION,
        "case_id": recovery.get("case_id") or continuation_gate.get("case_id"),
        "queue_id": recovery.get("queue_id") or continuation_gate.get("queue_id"),
        "continuation_gate_id": continuation_gate.get("continuation_gate_id"),
        "continuation_gate_verification_status": continuation_gate_verification.get(
            "status"
        ),
        "continuation_gate_verified": continuation_gate_verification.get("verified")
        is True,
        "gate_open": continuation_gate_verification.get("gate_open") is True,
        "safe_to_reenter_operations": continuation_gate_verification.get(
            "ready_for_delivery_continuation"
        )
        is True,
        "resume_operator": resume_operator or "system",
        "next_action": NEXT_ACTION,
    }


def _resume_blockers(
    recovery: dict[str, Any],
    continuation_gate: dict[str, Any],
    continuation_gate_verification: dict[str, Any],
) -> list[dict[str, Any]]:
    blockers = []
    if not recovery:
        blockers.append(_blocker("missing_recovery", "recovery artifact is missing"))
    if not continuation_gate:
        blockers.append(
            _blocker("missing_continuation_gate", "continuation gate is missing")
        )
    if not continuation_gate_verification:
        blockers.append(
            _blocker(
                "missing_continuation_gate_verification",
                "continuation gate verification is missing",
            )
        )
    if (
        continuation_gate_verification
        and continuation_gate_verification.get("verified") is not True
    ):
        blockers.extend(deepcopy(continuation_gate_verification.get("blockers") or []))
        blockers.append(
            _blocker(
                "continuation_gate_verification_blocked",
                "continuation gate verification did not pass",
            )
        )
    if (
        continuation_gate_verification
        and continuation_gate_verification.get("gate_open") is not True
    ):
        blockers.append(
            _blocker(
                "continuation_gate_not_open",
                "continuation gate verification is not open",
            )
        )
    if (
        continuation_gate_verification
        and continuation_gate_verification.get("ready_for_delivery_continuation")
        is not True
    ):
        blockers.append(
            _blocker(
                "not_ready_for_delivery_continuation",
                "continuation gate verification is not ready for delivery continuation",
            )
        )
    if (
        recovery
        and continuation_gate
        and recovery.get("queue_id") != continuation_gate.get("queue_id")
    ):
        blockers.append(
            _blocker(
                "continuation_gate_queue_mismatch",
                "continuation gate queue_id does not match recovery queue_id",
            )
        )
    if (
        continuation_gate
        and continuation_gate_verification
        and continuation_gate.get("continuation_gate_id")
        != continuation_gate_verification.get("continuation_gate_id")
    ):
        blockers.append(
            _blocker(
                "continuation_gate_id_mismatch",
                "continuation gate id does not match verification",
            )
        )
    return blockers


def build_case_delivery_recovery_resume_operations_snapshot(
    recovery: dict[str, Any],
    receipt: dict[str, Any] | None = None,
    closure: dict[str, Any] | None = None,
    audit_package: dict[str, Any] | None = None,
    audit_verification: dict[str, Any] | None = None,
    finalization: dict[str, Any] | None = None,
    finalization_verification: dict[str, Any] | None = None,
    continuation_gate: dict[str, Any] | None = None,
    continuation_gate_verification: dict[str, Any] | None = None,
    *,
    resume_operator: str | None = None,
) -> dict[str, Any]:
    safe_recovery = deepcopy(recovery or {})
    safe_receipt = deepcopy(receipt or {})
    safe_closure = deepcopy(closure or {})
    safe_audit_package = deepcopy(audit_package or {})
    safe_audit_verification = deepcopy(audit_verification or {})
    safe_finalization = deepcopy(finalization or {})
    safe_finalization_verification = deepcopy(finalization_verification or {})
    safe_continuation_gate = deepcopy(continuation_gate or {})
    if not safe_continuation_gate:
        gate_result = build_case_delivery_recovery_continuation_gate(
            safe_recovery,
            safe_receipt,
            safe_closure,
            safe_audit_package,
            safe_audit_verification,
            safe_finalization,
            safe_finalization_verification,
            gate_operator=resume_operator,
        )
        safe_continuation_gate = deepcopy(gate_result.get("continuation_gate") or {})
    safe_continuation_gate_verification = deepcopy(continuation_gate_verification or {})
    if not safe_continuation_gate_verification:
        safe_continuation_gate_verification = (
            verify_case_delivery_recovery_continuation_gate(
                safe_continuation_gate,
                safe_recovery,
                safe_receipt,
                safe_closure,
                safe_audit_package,
                safe_audit_verification,
                safe_finalization,
                safe_finalization_verification,
            )
        )

    blockers = _resume_blockers(
        safe_recovery, safe_continuation_gate, safe_continuation_gate_verification
    )
    if blockers:
        return {
            "schema": CASE_DELIVERY_RECOVERY_RESUME_OPERATIONS_RESULT_SCHEMA,
            "version": VERSION,
            "case_id": safe_recovery.get("case_id")
            or safe_continuation_gate.get("case_id"),
            "queue_id": safe_recovery.get("queue_id")
            or safe_continuation_gate.get("queue_id"),
            "continuation_gate_id": safe_continuation_gate.get("continuation_gate_id"),
            "status": "blocked",
            "safe_to_reenter_operations": False,
            "resume_snapshot": None,
            "continuation_gate_verification": safe_continuation_gate_verification,
            "blockers": blockers,
            "blocker_count": len(blockers),
            "next_action": "resolve_recovery_continuation_gate",
        }

    payload = _resume_payload(
        safe_recovery,
        safe_continuation_gate,
        safe_continuation_gate_verification,
        resume_operator,
    )
    payload_hash = sha256_text(canonical_json(payload))
    resume_snapshot = {
        **payload,
        "payload_sha256": payload_hash,
        "resume_snapshot_id": sha256_text(
            canonical_json({**payload, "payload_sha256": payload_hash})
        ),
    }
    return {
        "schema": CASE_DELIVERY_RECOVERY_RESUME_OPERATIONS_RESULT_SCHEMA,
        "version": VERSION,
        "case_id": resume_snapshot.get("case_id"),
        "queue_id": resume_snapshot.get("queue_id"),
        "continuation_gate_id": resume_snapshot.get("continuation_gate_id"),
        "status": "ready",
        "safe_to_reenter_operations": True,
        "resume_snapshot": resume_snapshot,
        "continuation_gate_verification": safe_continuation_gate_verification,
        "blockers": [],
        "blocker_count": 0,
        "next_action": NEXT_ACTION,
    }


def build_case_delivery_recovery_resume_operations_snapshot_from_request(
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
    continuation_gate = (
        safe_payload.get("continuation_gate")
        if isinstance(safe_payload.get("continuation_gate"), dict)
        else None
    )
    continuation_gate_verification = (
        safe_payload.get("continuation_gate_verification")
        if isinstance(safe_payload.get("continuation_gate_verification"), dict)
        else None
    )
    resume_operator = (
        safe_payload.get("resume_operator")
        if isinstance(safe_payload.get("resume_operator"), str)
        else None
    )
    return build_case_delivery_recovery_resume_operations_snapshot(
        recovery,
        receipt,
        closure,
        audit_package,
        audit_verification,
        finalization,
        finalization_verification,
        continuation_gate,
        continuation_gate_verification,
        resume_operator=resume_operator,
    )
