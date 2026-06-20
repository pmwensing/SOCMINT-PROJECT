from __future__ import annotations

from typing import Any

from . import database
from .connector_administration_events_v28_5 import find_connector
from .dossier_assembly_workspace_v21_0 import (
    _canonical,
    _ensure_storage,
    _json_details,
    _sha,
)

SCHEMA = "socmint.connector_adapter_contract.v29_3"
VERSION = "v29.3.0"
ACTIONS = (
    "connector_adapter_contract_created",
    "connector_adapter_contract_revised",
    "connector_adapter_conformance_evaluated",
)
ERROR_CLASSES = (
    "authorization_error",
    "scope_error",
    "rate_limit_error",
    "network_error",
    "upstream_error",
    "input_error",
    "output_error",
    "parsing_error",
    "provenance_error",
    "duplicate_error",
    "unknown_error",
)


def blocked(key: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key}],
        "connector_execution_performed": False,
        "connector_definition_mutated": False,
        "secret_values_exposed": False,
    }


def history() -> list[dict[str, Any]]:
    _ensure_storage()
    session = database.Session()
    try:
        rows = (
            session.query(database.AuditLog)
            .filter(database.AuditLog.action.in_(ACTIONS))
            .order_by(database.AuditLog.created_at.asc(), database.AuditLog.id.asc())
            .all()
        )
        return [
            {
                **_json_details(row),
                "audit_record_id": row.id,
                "actor": row.actor,
                "source_action": row.action,
                "audit_target_value": row.target_value,
                "recorded_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    finally:
        session.close()


def _record(
    action: str, actor: str, target: str, event: dict[str, Any], ip_address: str | None
) -> dict[str, Any]:
    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=actor,
            action=action,
            target_value=target,
            ip_address=ip_address,
            details=_canonical(event),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return {
            **event,
            "audit_record_id": row.id,
            "actor": actor,
            "source_action": action,
            "audit_target_value": target,
            "recorded_at": row.created_at.isoformat() if row.created_at else None,
        }
    finally:
        session.close()


def current_adapter_contracts() -> list[dict[str, Any]]:
    contracts: dict[str, dict[str, Any]] = {}
    for event in history():
        event_type = event.get("event_type")
        adapter_id = str(event.get("adapter_contract_id") or "")
        if (
            event_type in {"adapter_contract_created", "adapter_contract_revised"}
            and adapter_id
        ):
            previous = str(event.get("supersedes_adapter_contract_id") or "")
            if previous in contracts:
                contracts[previous] = {
                    **contracts[previous],
                    "adapter_status": "superseded",
                    "superseded_by_adapter_contract_id": adapter_id,
                }
            contracts[adapter_id] = {**event, "adapter_status": "active"}
    return sorted(
        contracts.values(), key=lambda item: str(item.get("connector_id") or "")
    )


def find_adapter_contract(adapter_contract_id: str) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in current_adapter_contracts()
            if item.get("adapter_contract_id") == adapter_contract_id
        ),
        None,
    )


def create_adapter_contract(
    *,
    actor: str,
    connector_id: str,
    capabilities: Any,
    input_schema: Any,
    output_schema: Any,
    authorization_requirements: Any,
    rate_limit_metadata: Any,
    error_classes: Any,
    provenance_requirements: Any,
    health_contract: Any,
    dossier_value_declaration: Any,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    connector = find_connector(connector_id)
    if connector is None or connector.get("connector_status") == "superseded":
        return blocked("current_connector_required")
    if confirmed is not True:
        return blocked("explicit_adapter_contract_confirmation_required")
    reason = str(reason or "").strip()
    if not reason:
        return blocked("administrative_reason_required")
    if any(
        item.get("connector_id") == connector_id
        and item.get("adapter_status") == "active"
        for item in current_adapter_contracts()
    ):
        return blocked("active_adapter_contract_already_exists")
    normalized_errors = sorted(
        {str(item).strip() for item in (error_classes or []) if str(item).strip()}
    )
    if any(item not in ERROR_CLASSES for item in normalized_errors):
        return blocked("adapter_error_class_invalid")
    definition = {
        "capabilities": sorted(
            {str(item).strip() for item in (capabilities or []) if str(item).strip()}
        ),
        "input_schema": input_schema if isinstance(input_schema, dict) else {},
        "output_schema": output_schema if isinstance(output_schema, dict) else {},
        "authorization_requirements": authorization_requirements
        if isinstance(authorization_requirements, dict)
        else {},
        "rate_limit_metadata": rate_limit_metadata
        if isinstance(rate_limit_metadata, dict)
        else {},
        "error_classes": normalized_errors,
        "provenance_requirements": provenance_requirements
        if isinstance(provenance_requirements, dict)
        else {},
        "health_contract": health_contract if isinstance(health_contract, dict) else {},
        "dossier_value_declaration": dossier_value_declaration
        if isinstance(dossier_value_declaration, dict)
        else {},
    }
    content = {
        "event_type": "adapter_contract_created",
        "connector_id": connector_id,
        "definition": definition,
        "definition_sha256": _sha(definition),
        "revision": 1,
        "supersedes_adapter_contract_id": None,
        "reason": reason,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "adapter_contract_id": f"adapter-contract-{digest[:24]}",
        "adapter_event_id": f"adapter-event-{digest[:24]}",
        "adapter_event_sha256": digest,
        "connector_execution_performed": False,
        "connector_definition_mutated": False,
        "secret_values_exposed": False,
    }
    result = _record(ACTIONS[0], actor, connector_id, event, ip_address)
    return {
        **result,
        "status": "adapter_contract_created",
        "next_action": "evaluate_adapter_conformance",
    }


def revise_adapter_contract(
    adapter_contract_id: str,
    *,
    actor: str,
    definition: Any,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    previous = find_adapter_contract(adapter_contract_id)
    if previous is None or previous.get("adapter_status") != "active":
        return blocked("active_adapter_contract_required")
    if confirmed is not True:
        return blocked("explicit_adapter_revision_confirmation_required")
    reason = str(reason or "").strip()
    if not reason:
        return blocked("administrative_reason_required")
    revised = definition if isinstance(definition, dict) else {}
    normalized_errors = sorted(
        {
            str(item).strip()
            for item in revised.get("error_classes", [])
            if str(item).strip()
        }
    )
    if any(item not in ERROR_CLASSES for item in normalized_errors):
        return blocked("adapter_error_class_invalid")
    revised["error_classes"] = normalized_errors
    binding = {
        "adapter_contract_id": adapter_contract_id,
        "adapter_event_id": previous.get("adapter_event_id"),
        "adapter_event_sha256": previous.get("adapter_event_sha256"),
        "definition_sha256": previous.get("definition_sha256"),
        "revision": previous.get("revision"),
    }
    content = {
        "event_type": "adapter_contract_revised",
        "connector_id": previous.get("connector_id"),
        "definition": revised,
        "definition_sha256": _sha(revised),
        "revision": int(previous.get("revision") or 1) + 1,
        "supersedes_adapter_contract_id": adapter_contract_id,
        "previous_adapter_binding": binding,
        "previous_adapter_binding_sha256": _sha(binding),
        "reason": reason,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "adapter_contract_id": f"adapter-contract-{digest[:24]}",
        "adapter_event_id": f"adapter-event-{digest[:24]}",
        "adapter_event_sha256": digest,
        "prior_adapter_event_mutated": False,
        "connector_execution_performed": False,
        "connector_definition_mutated": False,
        "secret_values_exposed": False,
    }
    result = _record(
        ACTIONS[1], actor, str(previous.get("connector_id")), event, ip_address
    )
    return {
        **result,
        "status": "adapter_contract_revised",
        "next_action": "reevaluate_adapter_conformance",
    }


def evaluate_adapter_conformance(
    *,
    actor: str,
    adapter_contract_id: str,
    observed_capabilities: Any,
    observed_input_schema: Any,
    observed_output_schema: Any,
    observed_error_classes: Any,
    observed_provenance_fields: Any,
    observed_health_fields: Any,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    contract = find_adapter_contract(adapter_contract_id)
    if contract is None or contract.get("adapter_status") != "active":
        return blocked("active_adapter_contract_required")
    if confirmed is not True:
        return blocked("explicit_conformance_evaluation_confirmation_required")
    reason = str(reason or "").strip()
    if not reason:
        return blocked("evaluation_reason_required")
    definition = contract.get("definition") or {}
    expected_caps = set(definition.get("capabilities") or [])
    observed_caps = {
        str(item).strip() for item in (observed_capabilities or []) if str(item).strip()
    }
    expected_errors = set(definition.get("error_classes") or [])
    observed_errors = {
        str(item).strip()
        for item in (observed_error_classes or [])
        if str(item).strip()
    }
    expected_prov = set(
        (definition.get("provenance_requirements") or {}).get("required_fields") or []
    )
    observed_prov = {
        str(item).strip()
        for item in (observed_provenance_fields or [])
        if str(item).strip()
    }
    expected_health = set(
        (definition.get("health_contract") or {}).get("required_fields") or []
    )
    observed_health = {
        str(item).strip()
        for item in (observed_health_fields or [])
        if str(item).strip()
    }
    findings = []
    for item in sorted(expected_caps - observed_caps):
        findings.append(
            {"severity": "high", "key": "missing_capability", "value": item}
        )
    for item in sorted(expected_errors - observed_errors):
        findings.append(
            {"severity": "medium", "key": "missing_error_class", "value": item}
        )
    for item in sorted(expected_prov - observed_prov):
        findings.append(
            {"severity": "high", "key": "missing_provenance_field", "value": item}
        )
    for item in sorted(expected_health - observed_health):
        findings.append(
            {"severity": "medium", "key": "missing_health_field", "value": item}
        )
    if not isinstance(observed_input_schema, dict) or not observed_input_schema:
        findings.append({"severity": "high", "key": "missing_observed_input_schema"})
    if not isinstance(observed_output_schema, dict) or not observed_output_schema:
        findings.append({"severity": "high", "key": "missing_observed_output_schema"})
    evaluation = {
        "conformant": not findings,
        "findings": findings,
        "finding_count": len(findings),
        "observed_capabilities": sorted(observed_caps),
        "observed_error_classes": sorted(observed_errors),
        "observed_provenance_fields": sorted(observed_prov),
        "observed_health_fields": sorted(observed_health),
    }
    binding = {
        "adapter_contract_id": adapter_contract_id,
        "adapter_event_sha256": contract.get("adapter_event_sha256"),
        "definition_sha256": contract.get("definition_sha256"),
        "revision": contract.get("revision"),
    }
    content = {
        "event_type": "adapter_conformance_evaluated",
        "connector_id": contract.get("connector_id"),
        "adapter_contract_id": adapter_contract_id,
        "adapter_binding": binding,
        "adapter_binding_sha256": _sha(binding),
        "evaluation": evaluation,
        "evaluation_sha256": _sha(evaluation),
        "reason": reason,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "adapter_evaluation_id": f"adapter-evaluation-{digest[:24]}",
        "adapter_event_id": f"adapter-event-{digest[:24]}",
        "adapter_event_sha256": digest,
        "connector_execution_performed": False,
        "connector_definition_mutated": False,
        "secret_values_exposed": False,
    }
    result = _record(ACTIONS[2], actor, adapter_contract_id, event, ip_address)
    return {
        **result,
        "status": "adapter_conformance_evaluated",
        "next_action": "approve_adapter_for_collection"
        if evaluation["conformant"]
        else "resolve_adapter_conformance_findings",
    }
