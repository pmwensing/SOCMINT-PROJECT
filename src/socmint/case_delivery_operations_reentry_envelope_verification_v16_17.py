from __future__ import annotations

from copy import deepcopy
from typing import Any

from .case_delivery_handoff_package_v15_1 import canonical_json
from .case_delivery_handoff_package_v15_1 import sha256_text
from .case_delivery_operations_reentry_envelope_v16_16 import NEXT_ACTION
from .case_delivery_operations_reentry_envelope_v16_16 import (
    build_case_delivery_operations_reentry_envelope,
)
from .case_delivery_recovery_resume_operations_snapshot_verification_v16_15 import (
    verify_case_delivery_recovery_resume_operations_snapshot,
)
from .case_delivery_recovery_v16_3 import build_case_delivery_recovery_from_request


CASE_DELIVERY_OPERATIONS_REENTRY_ENVELOPE_VERIFICATION_SCHEMA = (
    "socmint.case_delivery_operations_reentry_envelope_verification.v16_17"
)
VERSION = "v16.17.0"

REENTRY_ENVELOPE_PAYLOAD_FIELDS = (
    "schema",
    "version",
    "case_id",
    "queue_id",
    "resume_snapshot_id",
    "resume_snapshot_verification_status",
    "resume_snapshot_verified",
    "safe_to_reenter_operations",
    "ready_for_operations_dispatch",
    "reentry_operator",
    "next_action",
)


def _blocker(key: str, detail: str) -> dict[str, Any]:
    return {"key": key, "detail": detail}


def _envelope_payload(envelope: dict[str, Any]) -> dict[str, Any]:
    return {field: envelope.get(field) for field in REENTRY_ENVELOPE_PAYLOAD_FIELDS}


def verify_case_delivery_operations_reentry_envelope(
    reentry_envelope: dict[str, Any] | None,
    recovery: dict[str, Any],
    receipt: dict[str, Any] | None,
    closure: dict[str, Any] | None,
    audit_package: dict[str, Any] | None,
    audit_verification: dict[str, Any] | None,
    finalization: dict[str, Any] | None,
    finalization_verification: dict[str, Any] | None,
    continuation_gate: dict[str, Any] | None,
    continuation_gate_verification: dict[str, Any] | None,
    resume_snapshot: dict[str, Any] | None,
    resume_snapshot_verification: dict[str, Any] | None,
) -> dict[str, Any]:
    safe_envelope = deepcopy(reentry_envelope or {})
    safe_recovery = deepcopy(recovery or {})
    safe_receipt = deepcopy(receipt or {})
    safe_closure = deepcopy(closure or {})
    safe_audit_package = deepcopy(audit_package or {})
    safe_audit_verification = deepcopy(audit_verification or {})
    safe_finalization = deepcopy(finalization or {})
    safe_finalization_verification = deepcopy(finalization_verification or {})
    safe_continuation_gate = deepcopy(continuation_gate or {})
    safe_continuation_gate_verification = deepcopy(continuation_gate_verification or {})
    safe_resume_snapshot = deepcopy(resume_snapshot or {})
    snapshot_check = deepcopy(
        resume_snapshot_verification or {}
    ) or verify_case_delivery_recovery_resume_operations_snapshot(
        safe_resume_snapshot,
        safe_recovery,
        safe_receipt,
        safe_closure,
        safe_audit_package,
        safe_audit_verification,
        safe_finalization,
        safe_finalization_verification,
        safe_continuation_gate,
        safe_continuation_gate_verification,
    )
    blockers: list[dict[str, Any]] = []

    if not safe_envelope:
        blockers.append(
            _blocker(
                "missing_reentry_envelope", "operations re-entry envelope is missing"
            )
        )
    if snapshot_check.get("verified") is not True:
        blockers.extend(deepcopy(snapshot_check.get("blockers") or []))
        blockers.append(
            _blocker(
                "resume_snapshot_verification_blocked",
                "resume snapshot verification did not pass",
            )
        )
    if snapshot_check.get("safe_to_reenter_operations") is not True:
        blockers.append(
            _blocker(
                "not_safe_to_reenter_operations",
                "resume snapshot verification is not safe to re-enter operations",
            )
        )
    if snapshot_check.get("next_action") != "execute_delivery_operations":
        blockers.append(
            _blocker(
                "resume_snapshot_next_action_mismatch",
                "resume snapshot verification next_action is not execute_delivery_operations",
            )
        )

    expected_payload_hash = (
        sha256_text(canonical_json(_envelope_payload(safe_envelope)))
        if safe_envelope
        else None
    )
    if safe_envelope and safe_envelope.get("payload_sha256") != expected_payload_hash:
        blockers.append(
            _blocker(
                "payload_hash_mismatch",
                "re-entry envelope payload hash does not match envelope fields",
            )
        )

    expected_envelope_id = (
        sha256_text(
            canonical_json(
                {
                    **_envelope_payload(safe_envelope),
                    "payload_sha256": safe_envelope.get("payload_sha256"),
                }
            )
        )
        if safe_envelope
        else None
    )
    if (
        safe_envelope
        and safe_envelope.get("reentry_envelope_id") != expected_envelope_id
    ):
        blockers.append(
            _blocker(
                "reentry_envelope_id_mismatch",
                "re-entry envelope id does not match canonical envelope payload",
            )
        )

    if safe_envelope and safe_envelope.get("queue_id") != safe_recovery.get("queue_id"):
        blockers.append(
            _blocker(
                "queue_id_mismatch",
                "re-entry envelope queue_id does not match recovery queue",
            )
        )
    if safe_envelope and safe_envelope.get("case_id") != safe_recovery.get("case_id"):
        blockers.append(
            _blocker(
                "case_id_mismatch",
                "re-entry envelope case_id does not match recovery queue",
            )
        )
    if safe_envelope and safe_envelope.get(
        "resume_snapshot_id"
    ) != safe_resume_snapshot.get("resume_snapshot_id"):
        blockers.append(
            _blocker(
                "resume_snapshot_id_mismatch",
                "re-entry envelope resume_snapshot_id does not match resume snapshot",
            )
        )
    if (
        safe_envelope
        and snapshot_check.get("resume_snapshot_id")
        and safe_envelope.get("resume_snapshot_id")
        != snapshot_check.get("resume_snapshot_id")
    ):
        blockers.append(
            _blocker(
                "resume_snapshot_verification_id_mismatch",
                "re-entry envelope resume_snapshot_id does not match resume snapshot verification",
            )
        )
    if safe_envelope and safe_envelope.get(
        "resume_snapshot_verification_status"
    ) != snapshot_check.get("status"):
        blockers.append(
            _blocker(
                "resume_snapshot_verification_status_mismatch",
                "re-entry envelope verification status does not match resume snapshot verification",
            )
        )
    if safe_envelope and safe_envelope.get("resume_snapshot_verified") is not True:
        blockers.append(
            _blocker(
                "resume_snapshot_not_verified",
                "re-entry envelope resume_snapshot_verified flag is not true",
            )
        )
    if safe_envelope and safe_envelope.get("safe_to_reenter_operations") is not True:
        blockers.append(
            _blocker(
                "envelope_not_safe_to_reenter_operations",
                "re-entry envelope safe_to_reenter_operations flag is not true",
            )
        )
    if safe_envelope and safe_envelope.get("ready_for_operations_dispatch") is not True:
        blockers.append(
            _blocker(
                "not_ready_for_operations_dispatch",
                "re-entry envelope dispatch readiness flag is not true",
            )
        )
    if safe_envelope and safe_envelope.get("next_action") != NEXT_ACTION:
        blockers.append(
            _blocker(
                "next_action_mismatch",
                "re-entry envelope next_action is not dispatch_delivery_operations",
            )
        )

    status = "verified" if not blockers else "blocked"
    return {
        "schema": CASE_DELIVERY_OPERATIONS_REENTRY_ENVELOPE_VERIFICATION_SCHEMA,
        "version": VERSION,
        "case_id": safe_envelope.get("case_id") or safe_recovery.get("case_id"),
        "queue_id": safe_envelope.get("queue_id") or safe_recovery.get("queue_id"),
        "reentry_envelope_id": safe_envelope.get("reentry_envelope_id"),
        "resume_snapshot_id": safe_envelope.get("resume_snapshot_id")
        or safe_resume_snapshot.get("resume_snapshot_id"),
        "status": status,
        "verified": not blockers,
        "ready_for_operations_dispatch": not blockers,
        "next_action": NEXT_ACTION
        if not blockers
        else "resolve_operations_reentry_envelope",
        "blocker_count": len(blockers),
        "blockers": blockers,
        "resume_snapshot_verification": snapshot_check,
    }


def verify_case_delivery_operations_reentry_envelope_from_request(
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
    resume_snapshot = (
        safe_payload.get("resume_snapshot")
        if isinstance(safe_payload.get("resume_snapshot"), dict)
        else None
    )
    resume_snapshot_verification = (
        safe_payload.get("resume_snapshot_verification")
        if isinstance(safe_payload.get("resume_snapshot_verification"), dict)
        else None
    )
    reentry_envelope = (
        safe_payload.get("reentry_envelope")
        if isinstance(safe_payload.get("reentry_envelope"), dict)
        else None
    )
    if reentry_envelope is None:
        envelope_result = build_case_delivery_operations_reentry_envelope(
            recovery,
            receipt,
            closure,
            audit_package,
            audit_verification,
            finalization,
            finalization_verification,
            continuation_gate,
            continuation_gate_verification,
            resume_snapshot,
            resume_snapshot_verification,
            reentry_operator=safe_payload.get("reentry_operator"),
        )
        reentry_envelope = (
            envelope_result.get("reentry_envelope")
            if isinstance(envelope_result.get("reentry_envelope"), dict)
            else None
        )
    return verify_case_delivery_operations_reentry_envelope(
        reentry_envelope,
        recovery,
        receipt,
        closure,
        audit_package,
        audit_verification,
        finalization,
        finalization_verification,
        continuation_gate,
        continuation_gate_verification,
        resume_snapshot,
        resume_snapshot_verification,
    )
