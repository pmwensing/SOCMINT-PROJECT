from __future__ import annotations

from copy import deepcopy
from typing import Any

from .case_delivery_handoff_package_v15_1 import canonical_json
from .case_delivery_handoff_package_v15_1 import sha256_text
from .case_delivery_recovery_closure_record_v16_6 import (
    build_case_delivery_recovery_closure_record,
)
from .case_delivery_recovery_closure_record_verification_v16_7 import (
    verify_case_delivery_recovery_closure_record,
)
from .case_delivery_recovery_v16_3 import build_case_delivery_recovery_from_request


CASE_DELIVERY_RECOVERY_CLOSURE_AUDIT_PACKAGE_SCHEMA = (
    "socmint.case_delivery_recovery_closure_audit_package.v16_8"
)
CASE_DELIVERY_RECOVERY_CLOSURE_AUDIT_RESULT_SCHEMA = (
    "socmint.case_delivery_recovery_closure_audit_package.v16_8.result"
)
VERSION = "v16.8.0"

AUDIT_ARTIFACT_ORDER = (
    "recovery",
    "receipt",
    "closure",
    "closure_verification",
)


def _blocker(key: str, detail: str) -> dict[str, Any]:
    return {"key": key, "detail": detail}


def _artifact_manifest(
    name: str, artifact: dict[str, Any] | None, sequence: int
) -> dict[str, Any]:
    safe_artifact = deepcopy(artifact or {})
    payload = {
        "sequence": sequence,
        "name": name,
        "schema": safe_artifact.get("schema"),
        "case_id": safe_artifact.get("case_id"),
        "status": safe_artifact.get("status") or safe_artifact.get("state"),
        "sha256": sha256_text(canonical_json(safe_artifact)) if safe_artifact else None,
        "present": bool(safe_artifact),
    }
    return {**payload, "manifest_id": sha256_text(canonical_json(payload))}


def _audit_payload(
    recovery: dict[str, Any],
    receipt: dict[str, Any],
    closure: dict[str, Any],
    closure_verification: dict[str, Any],
    package_owner: str | None,
) -> dict[str, Any]:
    artifacts = {
        "recovery": recovery,
        "receipt": receipt,
        "closure": closure,
        "closure_verification": closure_verification,
    }
    manifest = [
        _artifact_manifest(name, artifacts.get(name), sequence)
        for sequence, name in enumerate(AUDIT_ARTIFACT_ORDER, start=1)
    ]
    return {
        "schema": CASE_DELIVERY_RECOVERY_CLOSURE_AUDIT_PACKAGE_SCHEMA,
        "version": VERSION,
        "case_id": recovery.get("case_id")
        or receipt.get("case_id")
        or closure.get("case_id"),
        "queue_id": recovery.get("queue_id")
        or receipt.get("queue_id")
        or closure.get("queue_id"),
        "receipt_id": receipt.get("receipt_id") or closure.get("receipt_id"),
        "closure_id": closure.get("closure_id"),
        "closure_verification_status": closure_verification.get("status"),
        "verified": closure_verification.get("verified") is True,
        "artifact_count": len(manifest),
        "package_owner": package_owner or "system",
        "manifest": manifest,
    }


def _package_blockers(
    recovery: dict[str, Any],
    receipt: dict[str, Any],
    closure: dict[str, Any],
    closure_verification: dict[str, Any],
) -> list[dict[str, Any]]:
    blockers = []
    if not recovery:
        blockers.append(_blocker("missing_recovery", "recovery artifact is missing"))
    if not receipt:
        blockers.append(_blocker("missing_receipt", "receipt artifact is missing"))
    if not closure:
        blockers.append(_blocker("missing_closure", "closure artifact is missing"))
    if not closure_verification:
        blockers.append(
            _blocker(
                "missing_closure_verification",
                "closure verification artifact is missing",
            )
        )
    if closure_verification and closure_verification.get("verified") is not True:
        blockers.extend(deepcopy(closure_verification.get("blockers") or []))
        blockers.append(
            _blocker(
                "closure_verification_blocked", "closure verification did not pass"
            )
        )
    if recovery and receipt and recovery.get("queue_id") != receipt.get("queue_id"):
        blockers.append(
            _blocker(
                "receipt_queue_mismatch",
                "receipt queue_id does not match recovery queue_id",
            )
        )
    if recovery and closure and recovery.get("queue_id") != closure.get("queue_id"):
        blockers.append(
            _blocker(
                "closure_queue_mismatch",
                "closure queue_id does not match recovery queue_id",
            )
        )
    if receipt and closure and receipt.get("receipt_id") != closure.get("receipt_id"):
        blockers.append(
            _blocker(
                "closure_receipt_mismatch", "closure receipt_id does not match receipt"
            )
        )
    return blockers


def build_case_delivery_recovery_closure_audit_package(
    recovery: dict[str, Any],
    receipt: dict[str, Any] | None = None,
    closure: dict[str, Any] | None = None,
    closure_verification: dict[str, Any] | None = None,
    *,
    package_owner: str | None = None,
) -> dict[str, Any]:
    safe_recovery = deepcopy(recovery or {})
    safe_receipt = deepcopy(receipt or {})
    safe_closure = deepcopy(closure or {})
    if not safe_closure:
        closure_result = build_case_delivery_recovery_closure_record(
            safe_recovery, safe_receipt, closer=package_owner
        )
        safe_closure = deepcopy(closure_result.get("closure") or {})
    safe_closure_verification = deepcopy(closure_verification or {})
    if not safe_closure_verification:
        safe_closure_verification = verify_case_delivery_recovery_closure_record(
            safe_closure, safe_recovery, safe_receipt
        )

    blockers = _package_blockers(
        safe_recovery, safe_receipt, safe_closure, safe_closure_verification
    )
    if blockers:
        return {
            "schema": CASE_DELIVERY_RECOVERY_CLOSURE_AUDIT_RESULT_SCHEMA,
            "version": VERSION,
            "case_id": safe_recovery.get("case_id")
            or safe_receipt.get("case_id")
            or safe_closure.get("case_id"),
            "queue_id": safe_recovery.get("queue_id")
            or safe_receipt.get("queue_id")
            or safe_closure.get("queue_id"),
            "status": "blocked",
            "packaged": False,
            "audit_package": None,
            "closure_verification": safe_closure_verification,
            "blockers": blockers,
            "blocker_count": len(blockers),
        }

    payload = _audit_payload(
        safe_recovery,
        safe_receipt,
        safe_closure,
        safe_closure_verification,
        package_owner,
    )
    package_hash = sha256_text(canonical_json(payload))
    audit_package = {
        **payload,
        "package_sha256": package_hash,
        "audit_package_id": sha256_text(
            canonical_json({**payload, "package_sha256": package_hash})
        ),
    }
    return {
        "schema": CASE_DELIVERY_RECOVERY_CLOSURE_AUDIT_RESULT_SCHEMA,
        "version": VERSION,
        "case_id": audit_package.get("case_id"),
        "queue_id": audit_package.get("queue_id"),
        "status": "packaged",
        "packaged": True,
        "audit_package": audit_package,
        "closure_verification": safe_closure_verification,
        "blockers": [],
        "blocker_count": 0,
    }


def build_case_delivery_recovery_closure_audit_package_from_request(
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
    closure_verification = (
        safe_payload.get("closure_verification")
        if isinstance(safe_payload.get("closure_verification"), dict)
        else None
    )
    package_owner = (
        safe_payload.get("package_owner")
        if isinstance(safe_payload.get("package_owner"), str)
        else None
    )
    return build_case_delivery_recovery_closure_audit_package(
        recovery,
        receipt,
        closure,
        closure_verification,
        package_owner=package_owner,
    )
