from __future__ import annotations

from copy import deepcopy
from typing import Any

from .case_delivery_handoff_package_v15_1 import canonical_json
from .case_delivery_handoff_package_v15_1 import sha256_text
from .case_delivery_recovery_continuation_gate_verification_v16_13 import (
    verify_case_delivery_recovery_continuation_gate,
)
from .case_delivery_recovery_resume_operations_snapshot_v16_14 import NEXT_ACTION
from .case_delivery_recovery_resume_operations_snapshot_v16_14 import (
    build_case_delivery_recovery_resume_operations_snapshot,
)
from .case_delivery_recovery_v16_3 import build_case_delivery_recovery_from_request


CASE_DELIVERY_RECOVERY_RESUME_OPERATIONS_SNAPSHOT_VERIFICATION_SCHEMA = "socmint.case_delivery_recovery_resume_operations_snapshot_verification.v16_15"
VERSION = "v16.15.0"

RESUME_SNAPSHOT_PAYLOAD_FIELDS = (
    "schema",
    "version",
    "case_id",
    "queue_id",
    "continuation_gate_id",
    "continuation_gate_verification_status",
    "continuation_gate_verified",
    "gate_open",
    "safe_to_reenter_operations",
    "resume_operator",
    "next_action",
)


def _blocker(key: str, detail: str) -> dict[str, Any]:
    return {"key": key, "detail": detail}


def _snapshot_payload(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {field: snapshot.get(field) for field in RESUME_SNAPSHOT_PAYLOAD_FIELDS}


def verify_case_delivery_recovery_resume_operations_snapshot(
    resume_snapshot: dict[str, Any] | None,
    recovery: dict[str, Any],
    receipt: dict[str, Any] | None,
    closure: dict[str, Any] | None,
    audit_package: dict[str, Any] | None,
    audit_verification: dict[str, Any] | None,
    finalization: dict[str, Any] | None,
    finalization_verification: dict[str, Any] | None,
    continuation_gate: dict[str, Any] | None,
    continuation_gate_verification: dict[str, Any] | None,
) -> dict[str, Any]:
    safe_snapshot = deepcopy(resume_snapshot or {})
    safe_recovery = deepcopy(recovery or {})
    safe_receipt = deepcopy(receipt or {})
    safe_closure = deepcopy(closure or {})
    safe_audit_package = deepcopy(audit_package or {})
    safe_audit_verification = deepcopy(audit_verification or {})
    safe_finalization = deepcopy(finalization or {})
    safe_finalization_verification = deepcopy(finalization_verification or {})
    safe_continuation_gate = deepcopy(continuation_gate or {})
    gate_check = deepcopy(continuation_gate_verification or {}) or verify_case_delivery_recovery_continuation_gate(
        safe_continuation_gate,
        safe_recovery,
        safe_receipt,
        safe_closure,
        safe_audit_package,
        safe_audit_verification,
        safe_finalization,
        safe_finalization_verification,
    )
    blockers: list[dict[str, Any]] = []

    if not safe_snapshot:
        blockers.append(_blocker("missing_resume_snapshot", "resume operations snapshot is missing"))
    if gate_check.get("verified") is not True:
        blockers.extend(deepcopy(gate_check.get("blockers") or []))
        blockers.append(_blocker("continuation_gate_verification_blocked", "continuation gate verification did not pass"))
    if gate_check.get("gate_open") is not True:
        blockers.append(_blocker("continuation_gate_not_open", "continuation gate verification is not open"))
    if gate_check.get("ready_for_delivery_continuation") is not True:
        blockers.append(_blocker("not_ready_for_delivery_continuation", "continuation gate verification is not ready for delivery continuation"))

    expected_payload_hash = sha256_text(canonical_json(_snapshot_payload(safe_snapshot))) if safe_snapshot else None
    if safe_snapshot and safe_snapshot.get("payload_sha256") != expected_payload_hash:
        blockers.append(_blocker("payload_hash_mismatch", "resume snapshot payload hash does not match snapshot fields"))

    expected_snapshot_id = (
        sha256_text(canonical_json({**_snapshot_payload(safe_snapshot), "payload_sha256": safe_snapshot.get("payload_sha256")}))
        if safe_snapshot
        else None
    )
    if safe_snapshot and safe_snapshot.get("resume_snapshot_id") != expected_snapshot_id:
        blockers.append(_blocker("resume_snapshot_id_mismatch", "resume snapshot id does not match canonical snapshot payload"))

    if safe_snapshot and safe_snapshot.get("queue_id") != safe_recovery.get("queue_id"):
        blockers.append(_blocker("queue_id_mismatch", "resume snapshot queue_id does not match recovery queue"))
    if safe_snapshot and safe_snapshot.get("case_id") != safe_recovery.get("case_id"):
        blockers.append(_blocker("case_id_mismatch", "resume snapshot case_id does not match recovery queue"))
    if safe_snapshot and safe_snapshot.get("continuation_gate_id") != safe_continuation_gate.get("continuation_gate_id"):
        blockers.append(_blocker("continuation_gate_id_mismatch", "resume snapshot continuation_gate_id does not match continuation gate"))
    if safe_snapshot and gate_check.get("continuation_gate_id") and safe_snapshot.get("continuation_gate_id") != gate_check.get("continuation_gate_id"):
        blockers.append(_blocker("continuation_gate_verification_id_mismatch", "resume snapshot continuation_gate_id does not match gate verification"))
    if safe_snapshot and safe_snapshot.get("continuation_gate_verification_status") != gate_check.get("status"):
        blockers.append(_blocker("continuation_gate_verification_status_mismatch", "resume snapshot verification status does not match gate verification"))
    if safe_snapshot and safe_snapshot.get("continuation_gate_verified") is not True:
        blockers.append(_blocker("continuation_gate_not_verified", "resume snapshot continuation_gate_verified flag is not true"))
    if safe_snapshot and safe_snapshot.get("gate_open") is not True:
        blockers.append(_blocker("gate_not_open", "resume snapshot gate_open flag is not true"))
    if safe_snapshot and safe_snapshot.get("safe_to_reenter_operations") is not True:
        blockers.append(_blocker("not_safe_to_reenter_operations", "resume snapshot safe_to_reenter_operations flag is not true"))
    if safe_snapshot and safe_snapshot.get("next_action") != NEXT_ACTION:
        blockers.append(_blocker("next_action_mismatch", "resume snapshot next_action is not execute_delivery_operations"))

    status = "verified" if not blockers else "blocked"
    return {
        "schema": CASE_DELIVERY_RECOVERY_RESUME_OPERATIONS_SNAPSHOT_VERIFICATION_SCHEMA,
        "version": VERSION,
        "case_id": safe_snapshot.get("case_id") or safe_recovery.get("case_id"),
        "queue_id": safe_snapshot.get("queue_id") or safe_recovery.get("queue_id"),
        "resume_snapshot_id": safe_snapshot.get("resume_snapshot_id"),
        "continuation_gate_id": safe_snapshot.get("continuation_gate_id") or safe_continuation_gate.get("continuation_gate_id"),
        "status": status,
        "verified": not blockers,
        "safe_to_reenter_operations": not blockers,
        "next_action": NEXT_ACTION if not blockers else "resolve_recovery_resume_snapshot",
        "blocker_count": len(blockers),
        "blockers": blockers,
        "continuation_gate_verification": gate_check,
    }


def verify_case_delivery_recovery_resume_operations_snapshot_from_request(case_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    safe_payload = deepcopy(payload or {})
    recovery = safe_payload.get("recovery") if isinstance(safe_payload.get("recovery"), dict) else None
    if recovery is None:
        recovery = build_case_delivery_recovery_from_request(case_id, safe_payload)
    receipt = safe_payload.get("receipt") if isinstance(safe_payload.get("receipt"), dict) else None
    closure = safe_payload.get("closure") if isinstance(safe_payload.get("closure"), dict) else None
    audit_package = safe_payload.get("audit_package") if isinstance(safe_payload.get("audit_package"), dict) else None
    audit_verification = safe_payload.get("audit_verification") if isinstance(safe_payload.get("audit_verification"), dict) else None
    finalization = safe_payload.get("finalization") if isinstance(safe_payload.get("finalization"), dict) else None
    finalization_verification = safe_payload.get("finalization_verification") if isinstance(safe_payload.get("finalization_verification"), dict) else None
    continuation_gate = safe_payload.get("continuation_gate") if isinstance(safe_payload.get("continuation_gate"), dict) else None
    continuation_gate_verification = safe_payload.get("continuation_gate_verification") if isinstance(safe_payload.get("continuation_gate_verification"), dict) else None
    resume_snapshot = safe_payload.get("resume_snapshot") if isinstance(safe_payload.get("resume_snapshot"), dict) else None
    if resume_snapshot is None:
        snapshot_result = build_case_delivery_recovery_resume_operations_snapshot(
            recovery,
            receipt,
            closure,
            audit_package,
            audit_verification,
            finalization,
            finalization_verification,
            continuation_gate,
            continuation_gate_verification,
            resume_operator=safe_payload.get("resume_operator"),
        )
        resume_snapshot = snapshot_result.get("resume_snapshot") if isinstance(snapshot_result.get("resume_snapshot"), dict) else None
    return verify_case_delivery_recovery_resume_operations_snapshot(
        resume_snapshot,
        recovery,
        receipt,
        closure,
        audit_package,
        audit_verification,
        finalization,
        finalization_verification,
        continuation_gate,
        continuation_gate_verification,
    )
