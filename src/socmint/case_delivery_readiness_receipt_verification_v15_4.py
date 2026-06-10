from __future__ import annotations

from copy import deepcopy
from typing import Any

from .case_delivery_handoff_package_v15_1 import build_case_delivery_handoff_package_from_request
from .case_delivery_handoff_package_v15_1 import canonical_json
from .case_delivery_handoff_package_v15_1 import sha256_text
from .case_delivery_handoff_verification_v15_2 import verify_case_delivery_handoff_package
from .case_delivery_readiness_receipt_v15_3 import build_case_delivery_readiness_receipt


CASE_DELIVERY_READINESS_RECEIPT_VERIFICATION_SCHEMA = (
    "socmint.case_delivery_readiness_receipt_verification.v15_4"
)
VERSION = "v15.4.0"
RECEIPT_PAYLOAD_FIELDS = (
    "schema",
    "version",
    "case_id",
    "delivery_id",
    "package_id",
    "gate_decision",
    "disposition",
    "verification_status",
    "verified",
    "issued_by",
    "operator",
    "accepted_for_delivery",
)


def _blocker(key: str, detail: str) -> dict[str, Any]:
    return {"key": key, "detail": detail}


def _receipt_payload(receipt: dict[str, Any]) -> dict[str, Any]:
    return {field: receipt.get(field) for field in RECEIPT_PAYLOAD_FIELDS}


def _signature_base(receipt: dict[str, Any]) -> dict[str, Any]:
    return {
        "payload_sha256": receipt.get("payload_sha256"),
        "package_id": receipt.get("package_id"),
        "case_id": receipt.get("case_id"),
        "version": "v15.3.0",
    }


def verify_case_delivery_readiness_receipt(
    receipt: dict[str, Any] | None,
    package: dict[str, Any],
) -> dict[str, Any]:
    safe_receipt = deepcopy(receipt or {})
    safe_package = deepcopy(package or {})
    package_verification = verify_case_delivery_handoff_package(safe_package)
    blockers = []

    if not safe_receipt:
        blockers.append(_blocker("missing_receipt", "readiness receipt is missing"))
    if not package_verification.get("verified"):
        blockers.append(_blocker("package_unverified", "handoff package verification did not pass"))

    expected_payload_hash = sha256_text(canonical_json(_receipt_payload(safe_receipt))) if safe_receipt else None
    if safe_receipt and safe_receipt.get("payload_sha256") != expected_payload_hash:
        blockers.append(_blocker("payload_hash_mismatch", "receipt payload hash does not match receipt fields"))

    expected_signature = sha256_text(canonical_json(_signature_base(safe_receipt))) if safe_receipt else None
    if safe_receipt and safe_receipt.get("signature_sha256") != expected_signature:
        blockers.append(_blocker("signature_hash_mismatch", "receipt signature hash does not match signature base"))

    expected_receipt_id = (
        sha256_text(canonical_json({**_signature_base(safe_receipt), "type": "delivery_readiness_receipt"}))
        if safe_receipt
        else None
    )
    if safe_receipt and safe_receipt.get("receipt_id") != expected_receipt_id:
        blockers.append(_blocker("receipt_id_mismatch", "receipt id does not match signature base"))

    if safe_receipt and safe_receipt.get("package_id") != safe_package.get("package_id"):
        blockers.append(_blocker("package_id_mismatch", "receipt package_id does not match handoff package"))
    if safe_receipt and safe_receipt.get("case_id") != safe_package.get("case_id"):
        blockers.append(_blocker("case_id_mismatch", "receipt case_id does not match handoff package"))
    if safe_receipt and safe_receipt.get("verified") is not True:
        blockers.append(_blocker("receipt_not_verified", "receipt verified flag is not true"))
    if safe_receipt and safe_receipt.get("accepted_for_delivery") is not True:
        blockers.append(_blocker("not_accepted_for_delivery", "receipt is not accepted for delivery"))

    status = "verified" if not blockers else "blocked"
    return {
        "schema": CASE_DELIVERY_READINESS_RECEIPT_VERIFICATION_SCHEMA,
        "version": VERSION,
        "case_id": safe_receipt.get("case_id") or safe_package.get("case_id"),
        "package_id": safe_receipt.get("package_id") or safe_package.get("package_id"),
        "receipt_id": safe_receipt.get("receipt_id"),
        "status": status,
        "verified": not blockers,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "package_verification": package_verification,
    }


def verify_case_delivery_readiness_receipt_from_request(case_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    safe_payload = deepcopy(payload or {})
    package = safe_payload.get("package") if isinstance(safe_payload.get("package"), dict) else None
    if package is None:
        package = build_case_delivery_handoff_package_from_request(case_id, safe_payload)
    receipt = safe_payload.get("receipt") if isinstance(safe_payload.get("receipt"), dict) else None
    if receipt is None:
        receipt_result = build_case_delivery_readiness_receipt(package, issuer=safe_payload.get("issuer"))
        receipt = receipt_result.get("receipt") if isinstance(receipt_result.get("receipt"), dict) else None
    return verify_case_delivery_readiness_receipt(receipt, package)
