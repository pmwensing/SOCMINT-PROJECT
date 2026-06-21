from __future__ import annotations

from copy import deepcopy
from typing import Any

from .case_delivery_handoff_package_v15_1 import canonical_json
from .case_delivery_handoff_package_v15_1 import sha256_text
from .case_delivery_recovery_resume_operations_snapshot_v16_14 import (
    build_case_delivery_recovery_resume_operations_snapshot,
)
from .case_delivery_recovery_resume_operations_snapshot_verification_v16_15 import (
    verify_case_delivery_recovery_resume_operations_snapshot,
)
from .case_delivery_recovery_v16_3 import build_case_delivery_recovery_from_request


CASE_DELIVERY_OPERATIONS_REENTRY_ENVELOPE_SCHEMA = (
    "socmint.case_delivery_operations_reentry_envelope.v16_16"
)
CASE_DELIVERY_OPERATIONS_REENTRY_ENVELOPE_RESULT_SCHEMA = (
    "socmint.case_delivery_operations_reentry_envelope.v16_16.result"
)
VERSION = "v16.16.0"
NEXT_ACTION = "dispatch_delivery_operations"


def _blocker(key: str, detail: str) -> dict[str, Any]:
    return {"key": key, "detail": detail}


def _reentry_payload(
    recovery: dict[str, Any],
    resume_snapshot: dict[str, Any],
    resume_snapshot_verification: dict[str, Any],
    reentry_operator: str | None,
) -> dict[str, Any]:
    return {
        "schema": CASE_DELIVERY_OPERATIONS_REENTRY_ENVELOPE_SCHEMA,
        "version": VERSION,
        "case_id": recovery.get("case_id") or resume_snapshot.get("case_id"),
        "queue_id": recovery.get("queue_id") or resume_snapshot.get("queue_id"),
        "resume_snapshot_id": resume_snapshot.get("resume_snapshot_id"),
        "resume_snapshot_verification_status": resume_snapshot_verification.get(
            "status"
        ),
        "resume_snapshot_verified": resume_snapshot_verification.get("verified")
        is True,
        "safe_to_reenter_operations": resume_snapshot_verification.get(
            "safe_to_reenter_operations"
        )
        is True,
        "ready_for_operations_dispatch": resume_snapshot_verification.get("next_action")
        == "execute_delivery_operations",
        "reentry_operator": reentry_operator or "system",
        "next_action": NEXT_ACTION,
    }


def _reentry_blockers(
    recovery: dict[str, Any],
    resume_snapshot: dict[str, Any],
    resume_snapshot_verification: dict[str, Any],
) -> list[dict[str, Any]]:
    blockers = []
    if not recovery:
        blockers.append(_blocker("missing_recovery", "recovery artifact is missing"))
    if not resume_snapshot:
        blockers.append(
            _blocker("missing_resume_snapshot", "resume snapshot is missing")
        )
    if not resume_snapshot_verification:
        blockers.append(
            _blocker(
                "missing_resume_snapshot_verification",
                "resume snapshot verification is missing",
            )
        )
    if (
        resume_snapshot_verification
        and resume_snapshot_verification.get("verified") is not True
    ):
        blockers.extend(deepcopy(resume_snapshot_verification.get("blockers") or []))
        blockers.append(
            _blocker(
                "resume_snapshot_verification_blocked",
                "resume snapshot verification did not pass",
            )
        )
    if (
        resume_snapshot_verification
        and resume_snapshot_verification.get("safe_to_reenter_operations") is not True
    ):
        blockers.append(
            _blocker(
                "not_safe_to_reenter_operations",
                "resume snapshot verification is not safe to re-enter operations",
            )
        )
    if (
        resume_snapshot_verification
        and resume_snapshot_verification.get("next_action")
        != "execute_delivery_operations"
    ):
        blockers.append(
            _blocker(
                "resume_snapshot_next_action_mismatch",
                "resume snapshot verification next_action is not execute_delivery_operations",
            )
        )
    if (
        recovery
        and resume_snapshot
        and recovery.get("queue_id") != resume_snapshot.get("queue_id")
    ):
        blockers.append(
            _blocker(
                "resume_snapshot_queue_mismatch",
                "resume snapshot queue_id does not match recovery queue_id",
            )
        )
    if (
        resume_snapshot
        and resume_snapshot_verification
        and resume_snapshot.get("resume_snapshot_id")
        != resume_snapshot_verification.get("resume_snapshot_id")
    ):
        blockers.append(
            _blocker(
                "resume_snapshot_id_mismatch",
                "resume snapshot id does not match verification",
            )
        )
    return blockers


def build_case_delivery_operations_reentry_envelope(
    recovery: dict[str, Any],
    receipt: dict[str, Any] | None = None,
    closure: dict[str, Any] | None = None,
    audit_package: dict[str, Any] | None = None,
    audit_verification: dict[str, Any] | None = None,
    finalization: dict[str, Any] | None = None,
    finalization_verification: dict[str, Any] | None = None,
    continuation_gate: dict[str, Any] | None = None,
    continuation_gate_verification: dict[str, Any] | None = None,
    resume_snapshot: dict[str, Any] | None = None,
    resume_snapshot_verification: dict[str, Any] | None = None,
    *,
    reentry_operator: str | None = None,
) -> dict[str, Any]:
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
    if not safe_resume_snapshot:
        snapshot_result = build_case_delivery_recovery_resume_operations_snapshot(
            safe_recovery,
            safe_receipt,
            safe_closure,
            safe_audit_package,
            safe_audit_verification,
            safe_finalization,
            safe_finalization_verification,
            safe_continuation_gate,
            safe_continuation_gate_verification,
            resume_operator=reentry_operator,
        )
        safe_resume_snapshot = deepcopy(snapshot_result.get("resume_snapshot") or {})
    safe_resume_snapshot_verification = deepcopy(resume_snapshot_verification or {})
    if not safe_resume_snapshot_verification:
        safe_resume_snapshot_verification = (
            verify_case_delivery_recovery_resume_operations_snapshot(
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
        )

    blockers = _reentry_blockers(
        safe_recovery, safe_resume_snapshot, safe_resume_snapshot_verification
    )
    if blockers:
        return {
            "schema": CASE_DELIVERY_OPERATIONS_REENTRY_ENVELOPE_RESULT_SCHEMA,
            "version": VERSION,
            "case_id": safe_recovery.get("case_id")
            or safe_resume_snapshot.get("case_id"),
            "queue_id": safe_recovery.get("queue_id")
            or safe_resume_snapshot.get("queue_id"),
            "resume_snapshot_id": safe_resume_snapshot.get("resume_snapshot_id"),
            "status": "blocked",
            "ready_for_operations_dispatch": False,
            "reentry_envelope": None,
            "resume_snapshot_verification": safe_resume_snapshot_verification,
            "blockers": blockers,
            "blocker_count": len(blockers),
            "next_action": "resolve_recovery_resume_snapshot",
        }

    payload = _reentry_payload(
        safe_recovery,
        safe_resume_snapshot,
        safe_resume_snapshot_verification,
        reentry_operator,
    )
    payload_hash = sha256_text(canonical_json(payload))
    reentry_envelope = {
        **payload,
        "payload_sha256": payload_hash,
        "reentry_envelope_id": sha256_text(
            canonical_json({**payload, "payload_sha256": payload_hash})
        ),
    }
    return {
        "schema": CASE_DELIVERY_OPERATIONS_REENTRY_ENVELOPE_RESULT_SCHEMA,
        "version": VERSION,
        "case_id": reentry_envelope.get("case_id"),
        "queue_id": reentry_envelope.get("queue_id"),
        "resume_snapshot_id": reentry_envelope.get("resume_snapshot_id"),
        "status": "ready_to_dispatch",
        "ready_for_operations_dispatch": True,
        "reentry_envelope": reentry_envelope,
        "resume_snapshot_verification": safe_resume_snapshot_verification,
        "blockers": [],
        "blocker_count": 0,
        "next_action": NEXT_ACTION,
    }


def build_case_delivery_operations_reentry_envelope_from_request(
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
    reentry_operator = (
        safe_payload.get("reentry_operator")
        if isinstance(safe_payload.get("reentry_operator"), str)
        else None
    )
    return build_case_delivery_operations_reentry_envelope(
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
        reentry_operator=reentry_operator,
    )
