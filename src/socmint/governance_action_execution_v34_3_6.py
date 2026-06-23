from __future__ import annotations

from typing import Any, Callable

from .action_eligibility_delegate_resolution_v34_1 import DELEGATE_REGISTRY
from .dossier_assembly_workspace_v21_0 import _sha
from .human_confirmation_framework_v34_2 import validate_confirmation

SCHEMA = "socmint.governance_action_execution.v34_3_6"
VERSION = "v34.6.0"

ACTION_FAMILIES = {
    "create_audience_contract": "audience_package_authorization",
    "assemble_dissemination_package": "audience_package_authorization",
    "record_authorization_policy_decision": "audience_package_authorization",
    "record_delivery_attempt": "delivery_retry",
    "record_delivery_receipt": "delivery_retry",
    "record_correction_intake": "feedback_correction",
    "record_recall_decision": "recall_retention",
    "record_retention_decision": "recall_retention",
}

Delegate = Callable[..., Any]
_CONSUMED_CONFIRMATIONS: set[str] = set()


def execute_confirmed_action(
    contract: dict[str, Any],
    confirmation_id: str,
    confirmed: bool,
    actor: str,
    delegates: dict[str, Delegate],
) -> dict[str, Any]:
    validation = validate_confirmation(contract, confirmation_id, confirmed)
    action = str(contract.get("action") or "")
    registered = DELEGATE_REGISTRY.get(action)
    if not validation["accepted"]:
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "status": "blocked",
            "action": action,
            "reason": validation["reason"],
            "execution_performed": False,
        }
    if confirmation_id in _CONSUMED_CONFIRMATIONS:
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "status": "duplicate_rejected",
            "action": action,
            "execution_performed": False,
        }
    service = str(contract.get("delegate_service") or "")
    if registered is None or registered["delegate_service"] != service:
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "status": "blocked",
            "action": action,
            "reason": "delegate_not_authorized",
            "execution_performed": False,
        }
    delegate = delegates.get(service)
    if delegate is None:
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "status": "delegate_unavailable",
            "action": action,
            "execution_performed": False,
        }

    kwargs = {
        **dict(contract.get("targets") or {}),
        **dict(contract.get("inputs") or {}),
    }
    result = delegate(**kwargs)
    _CONSUMED_CONFIRMATIONS.add(confirmation_id)
    result_reference = _sha(
        {
            "case_id": contract.get("case_id"),
            "action": action,
            "actor": actor,
            "confirmation_sha256": contract.get("confirmation_sha256"),
            "result_type": type(result).__name__,
        }
    )
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "executed",
        "case_id": contract.get("case_id"),
        "action": action,
        "action_family": ACTION_FAMILIES[action],
        "delegate_service": service,
        "actor": actor,
        "confirmation_sha256": contract.get("confirmation_sha256"),
        "result_reference_sha256": result_reference,
        "result": result,
        "execution_performed": True,
        "automatic_execution": False,
        "source_of_authority": "v32_delegate_service",
    }


def reset_confirmation_consumption_for_tests() -> None:
    _CONSUMED_CONFIRMATIONS.clear()
