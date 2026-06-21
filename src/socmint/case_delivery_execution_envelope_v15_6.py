from __future__ import annotations

from copy import deepcopy
from typing import Any

from .case_delivery_authorization_record_v15_5 import (
    build_case_delivery_authorization_record,
)
from .case_delivery_authorization_record_v15_5 import (
    build_case_delivery_authorization_record_from_request,
)
from .case_delivery_handoff_package_v15_1 import (
    build_case_delivery_handoff_package_from_request,
)
from .case_delivery_handoff_package_v15_1 import canonical_json
from .case_delivery_handoff_package_v15_1 import sha256_text
from .case_delivery_readiness_receipt_v15_3 import build_case_delivery_readiness_receipt


CASE_DELIVERY_EXECUTION_ENVELOPE_SCHEMA = (
    "socmint.case_delivery_execution_envelope.v15_6"
)
CASE_DELIVERY_EXECUTION_ENVELOPE_RESULT_SCHEMA = (
    "socmint.case_delivery_execution_envelope.v15_6.result"
)
VERSION = "v15.6.0"


def _blocker(key: str, detail: str) -> dict[str, Any]:
    return {"key": key, "detail": detail}


def _authorization_blockers(
    expected: dict[str, Any],
    supplied: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    blockers = []
    expected_authorization = (
        expected.get("authorization")
        if isinstance(expected.get("authorization"), dict)
        else {}
    )
    supplied_authorization = (
        supplied if isinstance(supplied, dict) else expected_authorization
    )

    if expected.get("status") != "authorized" or expected.get("authorized") is not True:
        blockers.append(
            _blocker(
                "authorization_blocked",
                "delivery authorization record did not authorize execution",
            )
        )
    if not supplied_authorization:
        blockers.append(
            _blocker("missing_authorization", "authorization record is missing")
        )

    for field in (
        "authorization_id",
        "payload_sha256",
        "case_id",
        "package_id",
        "receipt_id",
    ):
        if supplied_authorization and supplied_authorization.get(
            field
        ) != expected_authorization.get(field):
            blockers.append(
                _blocker(
                    f"{field}_mismatch",
                    f"authorization {field} does not match expected record",
                )
            )
    return blockers


def _authorized_delivery_links(package: dict[str, Any]) -> list[dict[str, Any]]:
    links = (
        package.get("delivery_links")
        if isinstance(package.get("delivery_links"), list)
        else []
    )
    authorized = []
    for row in links:
        if not isinstance(row, dict):
            continue
        authorized.append(
            {
                "label": row.get("label"),
                "href": row.get("href"),
                "authorized": True,
            }
        )
    return authorized


def build_case_delivery_execution_envelope(
    package: dict[str, Any],
    receipt: dict[str, Any] | None = None,
    authorization: dict[str, Any] | None = None,
    *,
    authorizer: str | None = None,
) -> dict[str, Any]:
    safe_package = deepcopy(package or {})
    safe_receipt = deepcopy(receipt or {})
    if not safe_receipt:
        receipt_result = build_case_delivery_readiness_receipt(
            safe_package, issuer=authorizer
        )
        safe_receipt = deepcopy(receipt_result.get("receipt") or {})

    expected_authorization = build_case_delivery_authorization_record(
        safe_package,
        safe_receipt,
        authorizer=authorizer,
    )
    supplied_authorization = deepcopy(authorization or {})
    blockers = _authorization_blockers(
        expected_authorization, supplied_authorization or None
    )
    if blockers:
        return {
            "schema": CASE_DELIVERY_EXECUTION_ENVELOPE_RESULT_SCHEMA,
            "version": VERSION,
            "case_id": safe_package.get("case_id"),
            "package_id": safe_package.get("package_id"),
            "receipt_id": safe_receipt.get("receipt_id"),
            "authorization_id": supplied_authorization.get("authorization_id"),
            "status": "blocked",
            "executable": False,
            "envelope": None,
            "authorization_result": expected_authorization,
            "blockers": blockers,
            "blocker_count": len(blockers),
        }

    authorization_record = (
        supplied_authorization or expected_authorization["authorization"]
    )
    manifest = (
        safe_package.get("manifest")
        if isinstance(safe_package.get("manifest"), dict)
        else {}
    )
    payload = {
        "schema": CASE_DELIVERY_EXECUTION_ENVELOPE_SCHEMA,
        "version": VERSION,
        "case_id": safe_package.get("case_id"),
        "delivery_id": safe_package.get("delivery_id"),
        "package_id": safe_package.get("package_id"),
        "receipt_id": safe_receipt.get("receipt_id"),
        "authorization_id": authorization_record.get("authorization_id"),
        "status": "ready_to_execute",
        "authorized_links": _authorized_delivery_links(safe_package),
        "manifest_file_count": manifest.get("file_count", 0),
    }
    payload_sha256 = sha256_text(canonical_json(payload))
    envelope = {
        **payload,
        "payload_sha256": payload_sha256,
        "execution_id": sha256_text(
            canonical_json({**payload, "payload_sha256": payload_sha256})
        ),
    }
    return {
        "schema": CASE_DELIVERY_EXECUTION_ENVELOPE_RESULT_SCHEMA,
        "version": VERSION,
        "case_id": safe_package.get("case_id"),
        "package_id": safe_package.get("package_id"),
        "receipt_id": safe_receipt.get("receipt_id"),
        "authorization_id": authorization_record.get("authorization_id"),
        "status": "ready_to_execute",
        "executable": True,
        "envelope": envelope,
        "authorization_result": expected_authorization,
        "blockers": [],
        "blocker_count": 0,
    }


def build_case_delivery_execution_envelope_from_request(
    case_id: str, payload: dict[str, Any]
) -> dict[str, Any]:
    safe_payload = deepcopy(payload or {})
    package = (
        safe_payload.get("package")
        if isinstance(safe_payload.get("package"), dict)
        else None
    )
    if package is None:
        package = build_case_delivery_handoff_package_from_request(
            case_id, safe_payload
        )
    receipt = (
        safe_payload.get("receipt")
        if isinstance(safe_payload.get("receipt"), dict)
        else None
    )
    authorization = (
        safe_payload.get("authorization")
        if isinstance(safe_payload.get("authorization"), dict)
        else None
    )
    authorizer = (
        safe_payload.get("authorizer")
        if isinstance(safe_payload.get("authorizer"), str)
        else None
    )
    if authorizer is None and isinstance(authorization, dict):
        authorizer = (
            authorization.get("authorized_by")
            if isinstance(authorization.get("authorized_by"), str)
            else None
        )
    if authorization is None:
        authorization_result = build_case_delivery_authorization_record_from_request(
            case_id, safe_payload
        )
        authorization = (
            authorization_result.get("authorization")
            if isinstance(authorization_result.get("authorization"), dict)
            else None
        )
    return build_case_delivery_execution_envelope(
        package,
        receipt,
        authorization,
        authorizer=authorizer,
    )
