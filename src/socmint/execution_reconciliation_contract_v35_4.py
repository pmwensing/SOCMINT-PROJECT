from __future__ import annotations

import re
from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from .dossier_assembly_workspace_v21_0 import _sha

SCHEMA = "socmint.execution_reconciliation_contract.v35_4"
VERSION = "v35.4.0"
HEX_64 = re.compile(r"^[0-9a-f]{64}$")
ALLOWED_FIELDS = frozenset(
    {
        "expected_state",
        "expected_version",
        "authoritative_record_ids",
        "result_reference_sha256",
        "workspace_sha256",
        "reconciliation_reason",
        "evidence_references",
    }
)


def _error(key: str, field: str) -> dict[str, str]:
    return {"key": key, "field": field}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _digest(value: Any, field: str, errors: list[dict[str, str]]) -> str:
    normalized = _text(value).lower()
    if not HEX_64.fullmatch(normalized):
        errors.append(_error("invalid_sha256", field))
    return normalized


def _version(value: Any, errors: list[dict[str, str]]) -> int | None:
    if isinstance(value, bool):
        errors.append(_error("invalid_integer", "expected_version"))
        return None
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        errors.append(_error("invalid_integer", "expected_version"))
        return None
    if normalized < 1:
        errors.append(_error("invalid_version", "expected_version"))
    return normalized


def _record_ids(
    value: Any,
    errors: list[dict[str, str]],
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        errors.append(_error("invalid_container_type", "authoritative_record_ids"))
        return {}
    normalized = {
        _text(key): deepcopy(item)
        for key, item in value.items()
        if _text(key) and item not in (None, "")
    }
    if not normalized:
        errors.append(_error("required", "authoritative_record_ids"))
    return normalized


def _evidence_references(
    value: Any,
    errors: list[dict[str, str]],
) -> list[dict[str, str]]:
    if not isinstance(value, list):
        errors.append(_error("invalid_container_type", "evidence_references"))
        return []
    normalized: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, Mapping):
            errors.append(_error("invalid_evidence_reference", "evidence_references"))
            continue
        reference_type = _text(item.get("reference_type"))
        reference_id = _text(item.get("reference_id"))
        description = _text(item.get("description"))
        if not reference_type or not reference_id:
            errors.append(_error("invalid_evidence_reference", "evidence_references"))
            continue
        reference = {
            "reference_type": reference_type[:64],
            "reference_id": reference_id[:512],
        }
        if description:
            reference["description"] = description[:1000]
        normalized.append(reference)
    if not normalized:
        errors.append(_error("required", "evidence_references"))
    return normalized


def validate_reconciliation_request(payload: Any) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    if not isinstance(payload, Mapping):
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "valid": False,
            "errors": [_error("invalid_container_type", "request")],
            "normalized": {},
            "validation_sha256": _sha(
                {"schema": SCHEMA, "version": VERSION, "valid": False}
            ),
        }

    unsupported = sorted(set(str(key) for key in payload) - ALLOWED_FIELDS)
    for field in unsupported:
        errors.append(_error("unsupported_field", field))

    expected_state = _text(payload.get("expected_state"))
    if expected_state != "uncertain":
        errors.append(_error("invalid_expected_state", "expected_state"))

    expected_version = _version(payload.get("expected_version"), errors)
    record_ids = _record_ids(payload.get("authoritative_record_ids"), errors)
    result_reference = _digest(
        payload.get("result_reference_sha256"),
        "result_reference_sha256",
        errors,
    )
    workspace_sha = _digest(
        payload.get("workspace_sha256"),
        "workspace_sha256",
        errors,
    )
    reason = _text(payload.get("reconciliation_reason"))
    if not reason:
        errors.append(_error("required", "reconciliation_reason"))
    evidence = _evidence_references(payload.get("evidence_references"), errors)

    normalized = {
        "expected_state": expected_state,
        "expected_version": expected_version,
        "authoritative_record_ids": record_ids,
        "result_reference_sha256": result_reference,
        "workspace_sha256": workspace_sha,
        "reconciliation_reason": reason[:2000],
        "evidence_references": evidence,
    }
    valid = not errors
    summary = {
        "schema": SCHEMA,
        "version": VERSION,
        "valid": valid,
        "errors": errors,
        "normalized": normalized if valid else {},
    }
    summary["validation_sha256"] = _sha(summary)
    return summary
