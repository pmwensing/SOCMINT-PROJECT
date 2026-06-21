from __future__ import annotations

from copy import deepcopy
from typing import Any

from .case_delivery_handoff_package_v15_1 import canonical_json
from .case_delivery_handoff_package_v15_1 import sha256_text
from .case_delivery_recovery_closure_audit_package_v16_8 import AUDIT_ARTIFACT_ORDER
from .case_delivery_recovery_closure_audit_package_v16_8 import (
    build_case_delivery_recovery_closure_audit_package,
)
from .case_delivery_recovery_closure_record_verification_v16_7 import (
    verify_case_delivery_recovery_closure_record,
)
from .case_delivery_recovery_v16_3 import build_case_delivery_recovery_from_request


CASE_DELIVERY_RECOVERY_CLOSURE_AUDIT_PACKAGE_VERIFICATION_SCHEMA = (
    "socmint.case_delivery_recovery_closure_audit_package_verification.v16_9"
)
VERSION = "v16.9.0"

AUDIT_PACKAGE_PAYLOAD_FIELDS = (
    "schema",
    "version",
    "case_id",
    "queue_id",
    "receipt_id",
    "closure_id",
    "closure_verification_status",
    "verified",
    "artifact_count",
    "package_owner",
    "manifest",
)

MANIFEST_PAYLOAD_FIELDS = (
    "sequence",
    "name",
    "schema",
    "case_id",
    "status",
    "sha256",
    "present",
)


def _blocker(key: str, detail: str) -> dict[str, Any]:
    return {"key": key, "detail": detail}


def _audit_payload(package: dict[str, Any]) -> dict[str, Any]:
    return {field: package.get(field) for field in AUDIT_PACKAGE_PAYLOAD_FIELDS}


def _manifest_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {field: row.get(field) for field in MANIFEST_PAYLOAD_FIELDS}


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


def _manifest_blockers(
    package: dict[str, Any], artifacts: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    blockers = []
    manifest = (
        package.get("manifest") if isinstance(package.get("manifest"), list) else []
    )
    if package.get("artifact_count") != len(manifest):
        blockers.append(
            _blocker(
                "artifact_count_mismatch",
                "audit package artifact_count does not match manifest",
            )
        )
    names = [row.get("name") for row in manifest if isinstance(row, dict)]
    if tuple(names) != AUDIT_ARTIFACT_ORDER:
        blockers.append(
            _blocker(
                "manifest_order_mismatch", "audit package manifest order is invalid"
            )
        )
    for sequence, name in enumerate(AUDIT_ARTIFACT_ORDER, start=1):
        row = (
            manifest[sequence - 1]
            if len(manifest) >= sequence and isinstance(manifest[sequence - 1], dict)
            else {}
        )
        expected = _artifact_manifest(name, artifacts.get(name), sequence)
        if not row:
            blockers.append(
                _blocker("missing_manifest_row", f"manifest row {name} is missing")
            )
            continue
        for field in MANIFEST_PAYLOAD_FIELDS:
            if row.get(field) != expected.get(field):
                blockers.append(
                    _blocker(
                        f"manifest_{field}_mismatch",
                        f"manifest {name} {field} does not match artifact",
                    )
                )
        expected_manifest_id = sha256_text(canonical_json(_manifest_payload(row)))
        if row.get("manifest_id") != expected_manifest_id:
            blockers.append(
                _blocker("manifest_id_mismatch", f"manifest id for {name} is invalid")
            )
    return blockers


def verify_case_delivery_recovery_closure_audit_package(
    audit_package: dict[str, Any] | None,
    recovery: dict[str, Any],
    receipt: dict[str, Any] | None,
    closure: dict[str, Any] | None,
    closure_verification: dict[str, Any] | None,
) -> dict[str, Any]:
    safe_package = deepcopy(audit_package or {})
    safe_recovery = deepcopy(recovery or {})
    safe_receipt = deepcopy(receipt or {})
    safe_closure = deepcopy(closure or {})
    safe_closure_verification = deepcopy(closure_verification or {})
    closure_check = verify_case_delivery_recovery_closure_record(
        safe_closure, safe_recovery, safe_receipt
    )
    blockers = []

    if not safe_package:
        blockers.append(_blocker("missing_audit_package", "audit package is missing"))
    if not closure_check.get("verified"):
        blockers.extend(deepcopy(closure_check.get("blockers") or []))
        blockers.append(
            _blocker(
                "closure_verification_blocked", "closure verification did not pass"
            )
        )

    expected_package_hash = (
        sha256_text(canonical_json(_audit_payload(safe_package)))
        if safe_package
        else None
    )
    if safe_package and safe_package.get("package_sha256") != expected_package_hash:
        blockers.append(
            _blocker(
                "package_hash_mismatch",
                "audit package hash does not match package fields",
            )
        )

    expected_package_id = (
        sha256_text(
            canonical_json(
                {
                    **_audit_payload(safe_package),
                    "package_sha256": safe_package.get("package_sha256"),
                }
            )
        )
        if safe_package
        else None
    )
    if safe_package and safe_package.get("audit_package_id") != expected_package_id:
        blockers.append(
            _blocker(
                "audit_package_id_mismatch",
                "audit package id does not match canonical package payload",
            )
        )

    if safe_package and safe_package.get("queue_id") != safe_recovery.get("queue_id"):
        blockers.append(
            _blocker(
                "queue_id_mismatch", "audit package queue_id does not match recovery"
            )
        )
    if safe_package and safe_package.get("case_id") != safe_recovery.get("case_id"):
        blockers.append(
            _blocker(
                "case_id_mismatch", "audit package case_id does not match recovery"
            )
        )
    if safe_package and safe_package.get("receipt_id") != safe_receipt.get(
        "receipt_id"
    ):
        blockers.append(
            _blocker(
                "receipt_id_mismatch", "audit package receipt_id does not match receipt"
            )
        )
    if safe_package and safe_package.get("closure_id") != safe_closure.get(
        "closure_id"
    ):
        blockers.append(
            _blocker(
                "closure_id_mismatch", "audit package closure_id does not match closure"
            )
        )
    if safe_package and safe_package.get(
        "closure_verification_status"
    ) != safe_closure_verification.get("status"):
        blockers.append(
            _blocker(
                "closure_verification_status_mismatch",
                "audit package verification status does not match closure verification",
            )
        )
    if safe_package and safe_package.get("verified") is not True:
        blockers.append(
            _blocker(
                "audit_package_not_verified", "audit package verified flag is not true"
            )
        )

    blockers.extend(
        _manifest_blockers(
            safe_package,
            {
                "recovery": safe_recovery,
                "receipt": safe_receipt,
                "closure": safe_closure,
                "closure_verification": safe_closure_verification,
            },
        )
    )

    status = "verified" if not blockers else "blocked"
    return {
        "schema": CASE_DELIVERY_RECOVERY_CLOSURE_AUDIT_PACKAGE_VERIFICATION_SCHEMA,
        "version": VERSION,
        "case_id": safe_package.get("case_id") or safe_recovery.get("case_id"),
        "queue_id": safe_package.get("queue_id") or safe_recovery.get("queue_id"),
        "audit_package_id": safe_package.get("audit_package_id"),
        "status": status,
        "verified": not blockers,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "closure_verification": closure_check,
    }


def verify_case_delivery_recovery_closure_audit_package_from_request(
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
    audit_package = (
        safe_payload.get("audit_package")
        if isinstance(safe_payload.get("audit_package"), dict)
        else None
    )
    if audit_package is None:
        package_result = build_case_delivery_recovery_closure_audit_package(
            recovery,
            receipt,
            closure,
            closure_verification,
            package_owner=safe_payload.get("package_owner"),
        )
        audit_package = (
            package_result.get("audit_package")
            if isinstance(package_result.get("audit_package"), dict)
            else None
        )
    return verify_case_delivery_recovery_closure_audit_package(
        audit_package, recovery, receipt, closure, closure_verification
    )
