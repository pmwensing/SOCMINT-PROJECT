from __future__ import annotations

import inspect
from collections.abc import Mapping
from copy import deepcopy
from typing import Any, Callable

from .action_contract_registry_v35_2 import (
    ACTION_CONTRACT_REGISTRY,
    SCHEMA,
    SYSTEM_FIELDS,
    VERSION,
    contract_for_action,
)
from .action_eligibility_delegate_resolution_v34_1 import DELEGATE_REGISTRY
from .dossier_assembly_workspace_v21_0 import _sha


def _matches(value: Any, kind: str) -> bool:
    if kind == "string":
        return isinstance(value, str)
    if kind == "string_list":
        return isinstance(value, list) and all(isinstance(item, str) for item in value)
    if kind == "mapping_list":
        return isinstance(value, list) and all(isinstance(item, dict) for item in value)
    return False


def _mapping_values(
    value: Any,
    field: str,
    errors: list[dict[str, Any]],
) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        errors.append(
            {
                "key": "invalid_container_type",
                "field": field,
                "expected": "mapping",
            }
        )
        return {}
    return deepcopy(dict(value))


def validate_action_payload(
    action: str,
    *,
    targets: Any = None,
    inputs: Any = None,
) -> dict[str, Any]:
    action = str(action or "")
    contract = contract_for_action(action)
    if contract is None:
        result = {
            "schema": SCHEMA,
            "version": VERSION,
            "action": action,
            "valid": False,
            "errors": [{"key": "unregistered_action", "field": None}],
            "normalized_fields": {},
        }
        return {**result, "validation_sha256": _sha(result)}

    errors: list[dict[str, Any]] = []
    target_values = _mapping_values(targets, "targets", errors)
    input_values = _mapping_values(inputs, "inputs", errors)

    for field in sorted(set(target_values) & set(input_values)):
        errors.append({"key": "field_supplied_twice", "field": field})

    combined = {**target_values, **input_values}
    definitions = contract["fields"]
    for field in sorted(set(combined) & SYSTEM_FIELDS):
        errors.append({"key": "system_field_not_operator_supplied", "field": field})
    for field in sorted(set(combined) - set(definitions) - SYSTEM_FIELDS):
        errors.append({"key": "unknown_field", "field": field})

    normalized: dict[str, Any] = {}
    for field, definition in definitions.items():
        present = field in combined
        value = combined.get(field)
        missing = value in (None, "", [], {})
        if definition["required"] and (not present or missing):
            errors.append({"key": "required_field_missing", "field": field})
            continue
        if not present:
            continue
        if not _matches(value, definition["kind"]):
            errors.append(
                {
                    "key": "invalid_field_type",
                    "field": field,
                    "expected": definition["kind"],
                }
            )
            continue
        normalized_value = value.strip() if isinstance(value, str) else deepcopy(value)
        if definition["required"] and normalized_value in ("", [], {}):
            errors.append({"key": "required_field_missing", "field": field})
            continue
        allowed = tuple(definition["values"])
        if allowed and normalized_value not in allowed:
            errors.append(
                {
                    "key": "invalid_field_value",
                    "field": field,
                    "allowed": list(allowed),
                }
            )
            continue
        normalized[field] = normalized_value

    for when_field, expected_value, required_field in contract["conditions"]:
        if normalized.get(when_field) == expected_value and normalized.get(
            required_field
        ) in (None, "", [], {}):
            errors.append(
                {
                    "key": "conditional_field_required",
                    "field": required_field,
                    "when_field": when_field,
                    "when_value": expected_value,
                }
            )

    errors.sort(
        key=lambda item: (str(item.get("field") or ""), str(item.get("key") or ""))
    )
    result = {
        "schema": SCHEMA,
        "version": VERSION,
        "action": action,
        "service": contract["service"],
        "actor_field": contract["actor_field"],
        "valid": not errors,
        "errors": errors,
        "normalized_fields": normalized if not errors else {},
        "operator_field_count": len(definitions),
        "system_fields": sorted(SYSTEM_FIELDS),
    }
    return {**result, "validation_sha256": _sha(result)}


def audit_registry_against_services(
    services: dict[str, Callable[..., Any]],
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    all_actions = set(DELEGATE_REGISTRY) | set(ACTION_CONTRACT_REGISTRY)
    for action in sorted(all_actions):
        delegate_entry = DELEGATE_REGISTRY.get(action)
        contract = ACTION_CONTRACT_REGISTRY.get(action)
        errors: list[str] = []
        if delegate_entry is None:
            errors.append("missing_delegate_registration")
        if contract is None:
            checks.append(
                {
                    "action": action,
                    "service": None,
                    "compatible": False,
                    "errors": ["missing_action_contract"],
                }
            )
            continue

        service_name = str(contract["service"])
        if delegate_entry is not None and service_name != delegate_entry["delegate_service"]:
            errors.append("service_registration_mismatch")
        service = services.get(service_name)
        if service is None:
            errors.append("service_unavailable")
        else:
            parameters = inspect.signature(service).parameters
            parameter_names = set(parameters)
            expected = set(contract["fields"]) | {
                str(contract["actor_field"]),
                "confirmed",
            }
            for field in sorted(expected - parameter_names):
                errors.append(f"service_parameter_missing:{field}")
            required_parameters = {
                name
                for name, parameter in parameters.items()
                if parameter.default is inspect.Parameter.empty
                and parameter.kind
                not in (
                    inspect.Parameter.VAR_POSITIONAL,
                    inspect.Parameter.VAR_KEYWORD,
                )
            }
            covered = set(contract["fields"]) | {
                str(contract["actor_field"]),
                "case_id",
                "confirmed",
                "ip_address",
            }
            for field in sorted(required_parameters - covered):
                errors.append(f"required_parameter_uncovered:{field}")

        checks.append(
            {
                "action": action,
                "service": service_name,
                "compatible": not errors,
                "errors": errors,
            }
        )

    report = {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "passed" if all(check["compatible"] for check in checks) else "failed",
        "action_count": len(checks),
        "compatible_count": sum(check["compatible"] for check in checks),
        "checks": checks,
    }
    return {**report, "audit_sha256": _sha(report)}
