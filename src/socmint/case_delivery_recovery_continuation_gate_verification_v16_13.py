from __future__ import annotations

from copy import deepcopy
from typing import Any

from .case_delivery_handoff_package_v15_1 import canonical_json
from .case_delivery_handoff_package_v15_1 import sha256_text
from .case_delivery_recovery_continuation_gate_v16_12 import NEXT_ACTION
from .case_delivery_recovery_continuation_gate_v16_12 import (
    build_case_delivery_recovery_continuation_gate,
)
from .case_delivery_recovery_finalization_record_verification_v16_11 import (
    verify_case_delivery_recovery_finalization_record,
)
from .case_delivery_recovery_v16_3 import build_case_delivery_recovery_from_request


CASE_DELIVERY_RECOVERY_CONTINUATION_GATE_VERIFICATION_SCHEMA = (
    "socmint.case_delivery_recovery_continuation_gate_verification.v16_13"
)
VERSION = "v16.13.0"

CONTINUATION_GATE_PAYLOAD_FIELDS = (
    "schema",
    "version",
    "case_id",
    "queue_id",
    "finalization_id",
    "audit_package_id",
    "finalization_verification_status",
    "finalization_verified",
    "ready_for_delivery_continuation",
    "gate_operator",
    "next_action",
    "gate_open",
)


def _blocker(key: str, detail: str) -> dict[str, Any]:
    return {"key": key, "detail": detail}


def _gate_payload(gate: dict[str, Any]) -> dict[str, Any]:
    return {field: gate.get(field) for field in CONTINUATION_GATE_PAYLOAD_FIELDS}


def verify_case_delivery_recovery_continuation_gate(
    continuation_gate: dict[str, Any] | None,
    recovery: dict[str, Any],
    receipt: dict[str, Any] | None,
    closure: dict[str, Any] | None,
    audit_package: dict[str, Any] | None,
    audit_verification: dict[str, Any] | None,
    finalization: dict[str, Any] | None,
    finalization_verification: dict[str, Any] | None,
) -> dict[str, Any]:
    safe_gate = deepcopy(continuation_gate or {})
    safe_recovery = deepcopy(recovery or {})
    safe_receipt = deepcopy(receipt or {})
    safe_closure = deepcopy(closure or {})
    safe_audit_package = deepcopy(audit_package or {})
    safe_audit_verification = deepcopy(audit_verification or {})
    safe_finalization = deepcopy(finalization or {})
    safe_finalization_verification = deepcopy(finalization_verification or {})
    finalization_check = (
        safe_finalization_verification
        or verify_case_delivery_recovery_finalization_record(
            safe_finalization,
            safe_recovery,
            safe_receipt,
            safe_closure,
            safe_audit_package,
            safe_audit_verification,
        )
    )
    blockers = []

    if not safe_gate:
        blockers.append(
            _blocker("missing_continuation_gate", "continuation gate is missing")
        )
    if not finalization_check.get("verified"):
        blockers.extend(deepcopy(finalization_check.get("blockers") or []))
        blockers.append(
            _blocker(
                "finalization_verification_blocked",
                "finalization verification did not pass",
            )
        )
    if finalization_check.get("ready_for_delivery_continuation") is not True:
        blockers.append(
            _blocker(
                "not_ready_for_delivery_continuation",
                "finalization verification is not ready for delivery continuation",
            )
        )

    expected_payload_hash = (
        sha256_text(canonical_json(_gate_payload(safe_gate))) if safe_gate else None
    )
    if safe_gate and safe_gate.get("payload_sha256") != expected_payload_hash:
        blockers.append(
            _blocker(
                "payload_hash_mismatch",
                "continuation gate payload hash does not match gate fields",
            )
        )

    expected_gate_id = (
        sha256_text(
            canonical_json(
                {
                    **_gate_payload(safe_gate),
                    "payload_sha256": safe_gate.get("payload_sha256"),
                }
            )
        )
        if safe_gate
        else None
    )
    if safe_gate and safe_gate.get("continuation_gate_id") != expected_gate_id:
        blockers.append(
            _blocker(
                "continuation_gate_id_mismatch",
                "continuation gate id does not match canonical gate payload",
            )
        )

    if safe_gate and safe_gate.get("queue_id") != safe_recovery.get("queue_id"):
        blockers.append(
            _blocker(
                "queue_id_mismatch",
                "continuation gate queue_id does not match recovery queue",
            )
        )
    if safe_gate and safe_gate.get("case_id") != safe_recovery.get("case_id"):
        blockers.append(
            _blocker(
                "case_id_mismatch",
                "continuation gate case_id does not match recovery queue",
            )
        )
    if safe_gate and safe_gate.get("finalization_id") != safe_finalization.get(
        "finalization_id"
    ):
        blockers.append(
            _blocker(
                "finalization_id_mismatch",
                "continuation gate finalization_id does not match finalization",
            )
        )
    if (
        safe_gate
        and finalization_check.get("finalization_id")
        and safe_gate.get("finalization_id")
        != finalization_check.get("finalization_id")
    ):
        blockers.append(
            _blocker(
                "finalization_verification_id_mismatch",
                "continuation gate finalization_id does not match finalization verification",
            )
        )
    if safe_gate and safe_gate.get("audit_package_id") != safe_audit_package.get(
        "audit_package_id"
    ):
        blockers.append(
            _blocker(
                "audit_package_id_mismatch",
                "continuation gate audit_package_id does not match audit package",
            )
        )
    if (
        safe_gate
        and finalization_check.get("audit_package_id")
        and safe_gate.get("audit_package_id")
        != finalization_check.get("audit_package_id")
    ):
        blockers.append(
            _blocker(
                "audit_verification_package_mismatch",
                "continuation gate audit_package_id does not match finalization verification",
            )
        )
    if safe_gate and safe_gate.get(
        "finalization_verification_status"
    ) != finalization_check.get("status"):
        blockers.append(
            _blocker(
                "finalization_verification_status_mismatch",
                "continuation gate verification status does not match finalization verification",
            )
        )
    if safe_gate and safe_gate.get("finalization_verified") is not True:
        blockers.append(
            _blocker(
                "finalization_not_verified",
                "continuation gate finalization_verified flag is not true",
            )
        )
    if safe_gate and safe_gate.get("ready_for_delivery_continuation") is not True:
        blockers.append(
            _blocker(
                "gate_not_ready_for_delivery_continuation",
                "continuation gate readiness flag is not true",
            )
        )
    if safe_gate and safe_gate.get("gate_open") is not True:
        blockers.append(
            _blocker("gate_not_open", "continuation gate open flag is not true")
        )
    if safe_gate and safe_gate.get("next_action") != NEXT_ACTION:
        blockers.append(
            _blocker(
                "next_action_mismatch",
                "continuation gate next_action is not resume_delivery_operations",
            )
        )

    status = "verified" if not blockers else "blocked"
    return {
        "schema": CASE_DELIVERY_RECOVERY_CONTINUATION_GATE_VERIFICATION_SCHEMA,
        "version": VERSION,
        "case_id": safe_gate.get("case_id") or safe_recovery.get("case_id"),
        "queue_id": safe_gate.get("queue_id") or safe_recovery.get("queue_id"),
        "continuation_gate_id": safe_gate.get("continuation_gate_id"),
        "finalization_id": safe_gate.get("finalization_id")
        or safe_finalization.get("finalization_id"),
        "status": status,
        "verified": not blockers,
        "gate_open": not blockers,
        "ready_for_delivery_continuation": not blockers,
        "next_action": NEXT_ACTION
        if not blockers
        else "resolve_recovery_continuation_gate",
        "blocker_count": len(blockers),
        "blockers": blockers,
        "finalization_verification": finalization_check,
    }


def verify_case_delivery_recovery_continuation_gate_from_request(
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
    if continuation_gate is None:
        gate_result = build_case_delivery_recovery_continuation_gate(
            recovery,
            receipt,
            closure,
            audit_package,
            audit_verification,
            finalization,
            finalization_verification,
            gate_operator=safe_payload.get("gate_operator"),
        )
        continuation_gate = (
            gate_result.get("continuation_gate")
            if isinstance(gate_result.get("continuation_gate"), dict)
            else None
        )
    return verify_case_delivery_recovery_continuation_gate(
        continuation_gate,
        recovery,
        receipt,
        closure,
        audit_package,
        audit_verification,
        finalization,
        finalization_verification,
    )
