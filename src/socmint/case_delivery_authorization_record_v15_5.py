from __future__ import annotations

from copy import deepcopy
from typing import Any

from .case_delivery_handoff_package_v15_1 import build_case_delivery_handoff_package_from_request
from .case_delivery_handoff_package_v15_1 import canonical_json
from .case_delivery_handoff_package_v15_1 import sha256_text
from .case_delivery_readiness_receipt_v15_3 import build_case_delivery_readiness_receipt
from .case_delivery_readiness_receipt_verification_v15_4 import verify_case_delivery_readiness_receipt


CASE_DELIVERY_AUTHORIZATION_RECORD_SCHEMA = "socmint.case_delivery_authorization_record.v15_5"
CASE_DELIVERY_AUTHORIZATION_RESULT_SCHEMA = "socmint.case_delivery_authorization_record.v15_5.result"
VERSION = "v15.5.0"


def _authorization_payload(
    package: dict[str, Any],
    receipt: dict[str, Any],
    receipt_verification: dict[str, Any],
    authorizer: str | None,
) -> dict[str, Any]:
    return {
        "schema": CASE_DELIVERY_AUTHORIZATION_RECORD_SCHEMA,
        "version": VERSION,
        "case_id": package.get("case_id"),
        "delivery_id": package.get("delivery_id"),
        "package_id": package.get("package_id"),
        "receipt_id": receipt.get("receipt_id"),
        "receipt_verification_status": receipt_verification.get("status"),
        "gate_decision": package.get("gate_decision"),
        "disposition": package.get("disposition"),
        "authorized_by": authorizer or receipt.get("issued_by") or "system",
        "authorized": receipt_verification.get("verified") is True,
    }


def build_case_delivery_authorization_record(
    package: dict[str, Any],
    receipt: dict[str, Any] | None = None,
    *,
    authorizer: str | None = None,
) -> dict[str, Any]:
    safe_package = deepcopy(package or {})
    safe_receipt = deepcopy(receipt or {})
    if not safe_receipt:
        receipt_result = build_case_delivery_readiness_receipt(safe_package, issuer=authorizer)
        safe_receipt = deepcopy(receipt_result.get("receipt") or {})
    receipt_verification = verify_case_delivery_readiness_receipt(safe_receipt, safe_package)

    if not receipt_verification.get("verified"):
        return {
            "schema": CASE_DELIVERY_AUTHORIZATION_RESULT_SCHEMA,
            "version": VERSION,
            "case_id": safe_package.get("case_id"),
            "package_id": safe_package.get("package_id"),
            "receipt_id": safe_receipt.get("receipt_id"),
            "status": "blocked",
            "authorized": False,
            "authorization": None,
            "receipt_verification": receipt_verification,
            "blockers": deepcopy(receipt_verification.get("blockers") or []),
            "blocker_count": receipt_verification.get("blocker_count", 0),
        }

    payload = _authorization_payload(safe_package, safe_receipt, receipt_verification, authorizer)
    payload_hash = sha256_text(canonical_json(payload))
    authorization = {
        **payload,
        "payload_sha256": payload_hash,
        "authorization_id": sha256_text(canonical_json({**payload, "payload_sha256": payload_hash})),
    }
    return {
        "schema": CASE_DELIVERY_AUTHORIZATION_RESULT_SCHEMA,
        "version": VERSION,
        "case_id": safe_package.get("case_id"),
        "package_id": safe_package.get("package_id"),
        "receipt_id": safe_receipt.get("receipt_id"),
        "status": "authorized",
        "authorized": True,
        "authorization": authorization,
        "receipt_verification": receipt_verification,
        "blockers": [],
        "blocker_count": 0,
    }


def build_case_delivery_authorization_record_from_request(case_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    safe_payload = deepcopy(payload or {})
    package = safe_payload.get("package") if isinstance(safe_payload.get("package"), dict) else None
    if package is None:
        package = build_case_delivery_handoff_package_from_request(case_id, safe_payload)
    receipt = safe_payload.get("receipt") if isinstance(safe_payload.get("receipt"), dict) else None
    authorizer = safe_payload.get("authorizer") if isinstance(safe_payload.get("authorizer"), str) else None
    return build_case_delivery_authorization_record(package, receipt, authorizer=authorizer)
