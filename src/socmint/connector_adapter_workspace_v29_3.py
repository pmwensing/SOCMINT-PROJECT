from __future__ import annotations

from collections import Counter
from typing import Any

from .connector_adapter_contract_v29_3 import ERROR_CLASSES, SCHEMA, VERSION, current_adapter_contracts, history
from .connector_administration_events_v28_5 import current_connectors


def build_connector_adapter_workspace() -> dict[str, Any]:
    contracts = current_adapter_contracts()
    events = history()
    connectors = current_connectors()
    connector_map = {str(item.get("connector_id")): item for item in connectors}
    active = [item for item in contracts if item.get("adapter_status") == "active"]
    evaluations = [item for item in events if item.get("event_type") == "adapter_conformance_evaluated"]
    latest_evaluation: dict[str, dict[str, Any]] = {}
    for event in evaluations:
        latest_evaluation[str(event.get("adapter_contract_id"))] = event
    findings = []
    summaries = []
    for contract in active:
        definition = contract.get("definition") or {}
        adapter_id = str(contract.get("adapter_contract_id") or "")
        connector_id = str(contract.get("connector_id") or "")
        connector = connector_map.get(connector_id)
        evaluation = latest_evaluation.get(adapter_id)
        if connector is None:
            findings.append({"severity":"high","key":"adapter_connector_missing","adapter_contract_id":adapter_id,"connector_id":connector_id})
        if not definition.get("capabilities"):
            findings.append({"severity":"high","key":"adapter_capabilities_missing","adapter_contract_id":adapter_id})
        if not definition.get("input_schema"):
            findings.append({"severity":"high","key":"adapter_input_schema_missing","adapter_contract_id":adapter_id})
        if not definition.get("output_schema"):
            findings.append({"severity":"high","key":"adapter_output_schema_missing","adapter_contract_id":adapter_id})
        if not definition.get("authorization_requirements"):
            findings.append({"severity":"medium","key":"adapter_authorization_requirements_missing","adapter_contract_id":adapter_id})
        if not definition.get("rate_limit_metadata"):
            findings.append({"severity":"medium","key":"adapter_rate_limit_metadata_missing","adapter_contract_id":adapter_id})
        if not definition.get("error_classes"):
            findings.append({"severity":"medium","key":"adapter_error_classes_missing","adapter_contract_id":adapter_id})
        if not definition.get("provenance_requirements"):
            findings.append({"severity":"high","key":"adapter_provenance_requirements_missing","adapter_contract_id":adapter_id})
        if not definition.get("health_contract"):
            findings.append({"severity":"medium","key":"adapter_health_contract_missing","adapter_contract_id":adapter_id})
        if not definition.get("dossier_value_declaration"):
            findings.append({"severity":"high","key":"adapter_dossier_value_missing","adapter_contract_id":adapter_id})
        if evaluation and not (evaluation.get("evaluation") or {}).get("conformant"):
            findings.append({"severity":"high","key":"adapter_nonconformant","adapter_contract_id":adapter_id,"finding_count":(evaluation.get("evaluation") or {}).get("finding_count",0)})
        summaries.append({
            "adapter_contract_id": adapter_id,
            "connector_id": connector_id,
            "connector_name": ((connector or {}).get("definition") or {}).get("name"),
            "revision": contract.get("revision"),
            "capabilities": definition.get("capabilities") or [],
            "authorization_requirements": definition.get("authorization_requirements") or {},
            "rate_limit_metadata": definition.get("rate_limit_metadata") or {},
            "error_classes": definition.get("error_classes") or [],
            "provenance_requirements": definition.get("provenance_requirements") or {},
            "health_contract": definition.get("health_contract") or {},
            "dossier_value_declaration": definition.get("dossier_value_declaration") or {},
            "latest_conformance": (evaluation or {}).get("evaluation"),
            "connector_execution_performed": False,
        })
    conformance_counts = Counter("conformant" if (item.get("evaluation") or {}).get("conformant") else "nonconformant" for item in evaluations)
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "ready",
        "adapter_contracts": contracts,
        "active_adapter_contracts": active,
        "adapter_contract_count": len(contracts),
        "active_adapter_contract_count": len(active),
        "adapter_summaries": summaries,
        "error_class_catalog": list(ERROR_CLASSES),
        "conformance_evaluations": evaluations[-250:],
        "conformance_evaluation_count": len(evaluations),
        "conformance_counts": dict(sorted(conformance_counts.items())),
        "adapter_findings": findings,
        "adapter_finding_count": len(findings),
        "adapter_history": events[-300:],
        "adapter_event_count": len(events),
        "connector_execution_available": False,
        "connector_definition_mutated": False,
        "secret_values_visible": False,
        "new_connectors_added_for_breadth": False,
        "case_access_scope_changed": False,
        "next_action": "review_connector_adapter_conformance",
    }
