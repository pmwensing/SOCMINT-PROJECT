from __future__ import annotations

from copy import deepcopy
from typing import Any

from .case_delivery_handoff_package_v15_1 import canonical_json
from .case_delivery_handoff_package_v15_1 import sha256_text
from .case_delivery_recovery_closure_audit_package_verification_v16_9 import (
    verify_case_delivery_recovery_closure_audit_package,
)
from .case_delivery_recovery_finalization_record_v16_10 import (
    build_case_delivery_recovery_finalization_record,
)
from .case_delivery_recovery_v16_3 import build_case_delivery_recovery_from_request


CASE_DELIVERY_RECOVERY_FINALIZATION_RECORD_VERIFICATION_SCHEMA = (
    "socmint.case_delivery_recovery_finalization_record_verification.v16_11"
)
VERSION = "v16.11.0"

FINALIZATION_PAYLOAD_FIELDS = (
    "schema",
    "version",
    "case_id",
    "queue_id",
    "receipt_id",
    "closure_id",
    "audit_package_id",
    "audit_verification_status",
    "ready_for_delivery_continuation",
    "finalized_by",
    "finalized",
)


def _blocker(key: str, detail: str) -> dict[str, Any]:
    return {"key": key, "detail": detail}


def _finalization_payload(finalization: dict[str, Any]) -> dict[str, Any]:
    return {field: finalization.get(field) for field in FINALIZATION_PAYLOAD_FIELDS}


def verify_case_delivery_recovery_finalization_record(
    finalization: dict[str, Any] | None,
    recovery: dict[str, Any],
    receipt: dict[str, Any] | None,
    closure: dict[str, Any] | None,
    audit_package: dict[str, Any] | None,
    audit_verification: dict[str, Any] | None,
) -> dict[str, Any]:
    safe_finalization = deepcopy(finalization or {})
    safe_recovery = deepcopy(recovery or {})
    safe_receipt = deepcopy(receipt or {})
    safe_closure = deepcopy(closure or {})
    safe_audit_package = deepcopy(audit_package or {})
    safe_audit_verification = deepcopy(audit_verification or {})
    audit_check = (
        safe_audit_verification
        or verify_case_delivery_recovery_closure_audit_package(
            safe_audit_package,
            safe_recovery,
            safe_receipt,
            safe_closure,
            None,
        )
    )
    blockers = []

    if not safe_finalization:
        blockers.append(
            _blocker("missing_finalization", "finalization record is missing")
        )
    if not audit_check.get("verified"):
        blockers.extend(deepcopy(audit_check.get("blockers") or []))
        blockers.append(
            _blocker(
                "audit_verification_blocked", "audit package verification did not pass"
            )
        )

    expected_payload_hash = (
        sha256_text(canonical_json(_finalization_payload(safe_finalization)))
        if safe_finalization
        else None
    )
    if (
        safe_finalization
        and safe_finalization.get("payload_sha256") != expected_payload_hash
    ):
        blockers.append(
            _blocker(
                "payload_hash_mismatch",
                "finalization payload hash does not match finalization fields",
            )
        )

    expected_finalization_id = (
        sha256_text(
            canonical_json(
                {
                    **_finalization_payload(safe_finalization),
                    "payload_sha256": safe_finalization.get("payload_sha256"),
                }
            )
        )
        if safe_finalization
        else None
    )
    if (
        safe_finalization
        and safe_finalization.get("finalization_id") != expected_finalization_id
    ):
        blockers.append(
            _blocker(
                "finalization_id_mismatch",
                "finalization id does not match canonical finalization payload",
            )
        )

    if safe_finalization and safe_finalization.get("queue_id") != safe_recovery.get(
        "queue_id"
    ):
        blockers.append(
            _blocker(
                "queue_id_mismatch",
                "finalization queue_id does not match recovery queue",
            )
        )
    if safe_finalization and safe_finalization.get("case_id") != safe_recovery.get(
        "case_id"
    ):
        blockers.append(
            _blocker(
                "case_id_mismatch", "finalization case_id does not match recovery queue"
            )
        )
    if safe_finalization and safe_finalization.get("receipt_id") != safe_receipt.get(
        "receipt_id"
    ):
        blockers.append(
            _blocker(
                "receipt_id_mismatch", "finalization receipt_id does not match receipt"
            )
        )
    if safe_finalization and safe_finalization.get("closure_id") != safe_closure.get(
        "closure_id"
    ):
        blockers.append(
            _blocker(
                "closure_id_mismatch", "finalization closure_id does not match closure"
            )
        )
    if safe_finalization and safe_finalization.get(
        "audit_package_id"
    ) != safe_audit_package.get("audit_package_id"):
        blockers.append(
            _blocker(
                "audit_package_id_mismatch",
                "finalization audit_package_id does not match audit package",
            )
        )
    if (
        safe_finalization
        and audit_check.get("audit_package_id")
        and safe_finalization.get("audit_package_id")
        != audit_check.get("audit_package_id")
    ):
        blockers.append(
            _blocker(
                "audit_verification_package_mismatch",
                "finalization audit_package_id does not match audit verification",
            )
        )
    if safe_finalization and safe_finalization.get(
        "audit_verification_status"
    ) != audit_check.get("status"):
        blockers.append(
            _blocker(
                "audit_verification_status_mismatch",
                "finalization audit verification status does not match verification",
            )
        )
    if (
        safe_finalization
        and safe_finalization.get("ready_for_delivery_continuation") is not True
    ):
        blockers.append(
            _blocker(
                "not_ready_for_delivery_continuation",
                "finalization readiness flag is not true",
            )
        )
    if safe_finalization and safe_finalization.get("finalized") is not True:
        blockers.append(
            _blocker("not_finalized", "finalization finalized flag is not true")
        )

    status = "verified" if not blockers else "blocked"
    return {
        "schema": CASE_DELIVERY_RECOVERY_FINALIZATION_RECORD_VERIFICATION_SCHEMA,
        "version": VERSION,
        "case_id": safe_finalization.get("case_id") or safe_recovery.get("case_id"),
        "queue_id": safe_finalization.get("queue_id") or safe_recovery.get("queue_id"),
        "finalization_id": safe_finalization.get("finalization_id"),
        "audit_package_id": safe_finalization.get("audit_package_id")
        or safe_audit_package.get("audit_package_id"),
        "status": status,
        "verified": not blockers,
        "ready_for_delivery_continuation": not blockers,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "audit_verification": audit_check,
    }


def verify_case_delivery_recovery_finalization_record_from_request(
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
    if finalization is None:
        finalization_result = build_case_delivery_recovery_finalization_record(
            recovery,
            receipt,
            closure,
            audit_package,
            audit_verification,
            finalizer=safe_payload.get("finalizer"),
        )
        finalization = (
            finalization_result.get("finalization")
            if isinstance(finalization_result.get("finalization"), dict)
            else None
        )
    return verify_case_delivery_recovery_finalization_record(
        finalization,
        recovery,
        receipt,
        closure,
        audit_package,
        audit_verification,
    )
