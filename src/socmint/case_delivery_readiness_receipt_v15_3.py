from __future__ import annotations

from copy import deepcopy
from typing import Any

from .case_delivery_handoff_package_v15_1 import build_case_delivery_handoff_package_from_request
from .case_delivery_handoff_package_v15_1 import canonical_json
from .case_delivery_handoff_package_v15_1 import sha256_text
from .case_delivery_handoff_verification_v15_2 import verify_case_delivery_handoff_package


CASE_DELIVERY_READINESS_RECEIPT_SCHEMA = "socmint.case_delivery_readiness_receipt.v15_3"
CASE_DELIVERY_READINESS_RECEIPT_RESULT_SCHEMA = "socmint.case_delivery_readiness_receipt.v15_3.result"
VERSION = "v15.3.0"


def _receipt_payload(package: dict[str, Any], verification: dict[str, Any], issuer: str | None) -> dict[str, Any]:
    operator_receipt = package.get("operator_receipt") if isinstance(package.get("operator_receipt"), dict) else {}
    return {
        "schema": CASE_DELIVERY_READINESS_RECEIPT_SCHEMA,
        "version": VERSION,
        "case_id": package.get("case_id"),
        "delivery_id": package.get("delivery_id"),
        "package_id": package.get("package_id"),
        "gate_decision": package.get("gate_decision"),
        "disposition": package.get("disposition"),
        "verification_status": verification.get("status"),
        "verified": verification.get("verified") is True,
        "issued_by": issuer or operator_receipt.get("operator") or "system",
        "operator": operator_receipt.get("operator") or "unassigned",
        "accepted_for_delivery": operator_receipt.get("accepted_for_delivery") is True,
    }


def build_case_delivery_readiness_receipt(
    package: dict[str, Any],
    *,
    issuer: str | None = None,
) -> dict[str, Any]:
    safe_package = deepcopy(package or {})
    verification = verify_case_delivery_handoff_package(safe_package)
    if not verification.get("verified"):
        return {
            "schema": CASE_DELIVERY_READINESS_RECEIPT_RESULT_SCHEMA,
            "version": VERSION,
            "case_id": safe_package.get("case_id"),
            "package_id": safe_package.get("package_id"),
            "status": "blocked",
            "receipt": None,
            "verification": verification,
            "blockers": deepcopy(verification.get("blockers") or []),
            "blocker_count": verification.get("blocker_count", 0),
        }

    payload = _receipt_payload(safe_package, verification, issuer)
    payload_hash = sha256_text(canonical_json(payload))
    signature_base = {
        "payload_sha256": payload_hash,
        "package_id": payload.get("package_id"),
        "case_id": payload.get("case_id"),
        "version": VERSION,
    }
    receipt = {
        **payload,
        "payload_sha256": payload_hash,
        "signature_algorithm": "sha256-canonical-json",
        "signature_sha256": sha256_text(canonical_json(signature_base)),
        "receipt_id": sha256_text(canonical_json({**signature_base, "type": "delivery_readiness_receipt"})),
    }
    return {
        "schema": CASE_DELIVERY_READINESS_RECEIPT_RESULT_SCHEMA,
        "version": VERSION,
        "case_id": safe_package.get("case_id"),
        "package_id": safe_package.get("package_id"),
        "status": "issued",
        "receipt": receipt,
        "verification": verification,
        "blockers": [],
        "blocker_count": 0,
    }


def build_case_delivery_readiness_receipt_from_request(case_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    safe_payload = deepcopy(payload or {})
    package = safe_payload.get("package") if isinstance(safe_payload.get("package"), dict) else None
    if package is None:
        package = build_case_delivery_handoff_package_from_request(case_id, safe_payload)
    issuer = safe_payload.get("issuer") if isinstance(safe_payload.get("issuer"), str) else None
    return build_case_delivery_readiness_receipt(package, issuer=issuer)
