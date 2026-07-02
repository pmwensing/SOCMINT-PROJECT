from __future__ import annotations

import inspect
from typing import Any, Callable

from .action_eligibility_delegate_resolution_v34_1 import DELEGATE_REGISTRY
from .dossier_assembly_workspace_v21_0 import _sha
from .durable_execution_ledger_v35_1 import (
    create_execution,
    reset_execution_ledger_for_tests as reset_durable_execution_ledger_for_tests,
    transition_execution,
)
from .governance_execution_hardening_v34_8 import (
    authoritative_record_ids,
    record_execution_result,
    refreshed_workspace,
    reset_execution_ledger_for_tests as reset_v34_execution_audit_for_tests,
)
from .human_confirmation_framework_v34_2 import validate_confirmation

SCHEMA = "socmint.governance_action_execution.v34_3_6"
VERSION = "v35.1.0"

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


def _delegate_kwargs(
    delegate: Delegate,
    contract: dict[str, Any],
    actor: str,
) -> dict[str, Any]:
    payload = {
        **dict(contract.get("targets") or {}),
        **dict(contract.get("inputs") or {}),
    }
    payload.setdefault("case_id", contract.get("case_id"))
    payload.setdefault("confirmed", True)
    parameters = inspect.signature(delegate).parameters
    for actor_parameter in ("actor", "reviewer", "operator", "recorder"):
        if actor_parameter in parameters:
            payload.setdefault(actor_parameter, actor)
            break
    if any(
        item.kind == inspect.Parameter.VAR_KEYWORD
        for item in parameters.values()
    ):
        return payload
    return {key: value for key, value in payload.items() if key in parameters}


def _ledger_claim(execution: dict[str, Any]) -> dict[str, Any]:
    return {
        "audit_record_id": execution.get("latest_ledger_record_id"),
        "recorded_at": execution.get("latest_recorded_at"),
        "execution_record_id": execution.get("execution_record_id"),
        "execution_id": execution.get("execution_id"),
    }


def _blocked(action: str, reason: str, status: str = "blocked") -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": status,
        "action": action,
        "reason": reason,
        "execution_performed": False,
        "automatic_retry": False,
    }


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
        return _blocked(action, validation["reason"])

    service = str(contract.get("delegate_service") or "")
    if registered is None or registered["delegate_service"] != service:
        return _blocked(action, "delegate_not_authorized")

    delegate = delegates.get(service)
    if delegate is None:
        return _blocked(action, "delegate_unavailable", "delegate_unavailable")

    confirmation_sha256 = str(contract.get("confirmation_sha256") or "")
    case_id = str(contract.get("case_id") or "")
    execution = create_execution(
        confirmation_sha256=confirmation_sha256,
        actor=actor,
        case_id=case_id,
        governance_action=action,
        delegate_service=service,
    )
    if not execution["created"]:
        return {
            **_blocked(action, "confirmation_already_consumed", "duplicate_rejected"),
            "case_id": case_id,
            "delegate_service": service,
            "execution_id": execution["execution_id"],
            "execution_state": execution["state"],
            "state_version": execution["state_version"],
            "identity_conflict": execution.get("identity_conflict", False),
            "durable_replay_protection": True,
        }

    try:
        kwargs = _delegate_kwargs(delegate, contract, actor)
    except Exception as exc:
        failed = transition_execution(
            execution_id=execution["execution_id"],
            expected_state="pending",
            expected_version=execution["state_version"],
            new_state="failed",
            actor=actor,
            reason="delegate_argument_preparation_failed",
            metadata={"exception_type": type(exc).__name__},
        )
        return {
            **_blocked(action, "delegate_argument_preparation_failed", "failed"),
            "case_id": case_id,
            "delegate_service": service,
            "execution_id": execution["execution_id"],
            "execution_state": failed["state"],
            "state_version": failed["state_version"],
            "confirmation_claim_audit": _ledger_claim(execution),
            "durable_replay_protection": True,
        }

    running = transition_execution(
        execution_id=execution["execution_id"],
        expected_state="pending",
        expected_version=execution["state_version"],
        new_state="running",
        actor=actor,
        reason="authoritative_delegate_invocation_started",
        metadata={"delegate_arguments": sorted(kwargs)},
    )

    try:
        result = delegate(**kwargs)
    except Exception as exc:
        uncertain = transition_execution(
            execution_id=execution["execution_id"],
            expected_state="running",
            expected_version=running["state_version"],
            new_state="uncertain",
            actor=actor,
            reason="delegate_outcome_not_confirmed",
            metadata={"exception_type": type(exc).__name__},
        )
        return {
            **_blocked(action, "delegate_outcome_not_confirmed", "uncertain"),
            "case_id": case_id,
            "action_family": ACTION_FAMILIES[action],
            "delegate_service": service,
            "delegate_arguments": sorted(kwargs),
            "actor": actor,
            "confirmation_sha256": confirmation_sha256,
            "confirmation_claim_audit": _ledger_claim(execution),
            "execution_id": execution["execution_id"],
            "execution_state": uncertain["state"],
            "state_version": uncertain["state_version"],
            "execution_attempted": True,
            "external_effect_unknown": True,
            "durable_replay_protection": True,
            "source_of_authority": "v32_delegate_service",
        }

    result_reference = _sha(
        {
            "case_id": case_id,
            "action": action,
            "actor": actor,
            "confirmation_sha256": confirmation_sha256,
            "result_type": type(result).__name__,
        }
    )
    record_ids = authoritative_record_ids(result)
    try:
        execution_audit = record_execution_result(
            actor=actor,
            case_id=case_id,
            action=action,
            confirmation_sha256=confirmation_sha256,
            delegate_service=service,
            result_reference_sha256=result_reference,
            authoritative_record_ids=record_ids,
        )
    except Exception as exc:
        uncertain = transition_execution(
            execution_id=execution["execution_id"],
            expected_state="running",
            expected_version=running["state_version"],
            new_state="uncertain",
            actor=actor,
            reason="delegate_result_persistence_failed",
            metadata={
                "exception_type": type(exc).__name__,
                "result_reference_sha256": result_reference,
                "authoritative_record_ids": record_ids,
            },
        )
        return {
            **_blocked(action, "delegate_result_persistence_failed", "uncertain"),
            "case_id": case_id,
            "action_family": ACTION_FAMILIES[action],
            "delegate_service": service,
            "delegate_arguments": sorted(kwargs),
            "actor": actor,
            "confirmation_sha256": confirmation_sha256,
            "confirmation_claim_audit": _ledger_claim(execution),
            "execution_id": execution["execution_id"],
            "execution_state": uncertain["state"],
            "state_version": uncertain["state_version"],
            "execution_attempted": True,
            "external_effect_unknown": True,
            "authoritative_record_ids": record_ids,
            "result_reference_sha256": result_reference,
            "durable_replay_protection": True,
            "source_of_authority": "v32_delegate_service",
        }

    succeeded = transition_execution(
        execution_id=execution["execution_id"],
        expected_state="running",
        expected_version=running["state_version"],
        new_state="succeeded",
        actor=actor,
        reason="authoritative_delegate_result_persisted",
        metadata={
            "execution_audit_record_id": execution_audit.get("audit_record_id"),
            "result_reference_sha256": result_reference,
            "authoritative_record_ids": record_ids,
        },
    )

    workspace = refreshed_workspace(case_id)
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "executed",
        "case_id": case_id,
        "action": action,
        "action_family": ACTION_FAMILIES[action],
        "delegate_service": service,
        "delegate_arguments": sorted(kwargs),
        "actor": actor,
        "confirmation_sha256": confirmation_sha256,
        "confirmation_claim_audit": _ledger_claim(execution),
        "execution_audit": execution_audit,
        "execution_id": execution["execution_id"],
        "execution_state": succeeded["state"],
        "state_version": succeeded["state_version"],
        "execution_ledger_consistent": succeeded["ledger_consistent"],
        "authoritative_record_ids": record_ids,
        "result_reference_sha256": result_reference,
        "result": result,
        "workspace": workspace,
        "workspace_sha256": workspace.get("workspace_sha256"),
        "execution_performed": True,
        "execution_attempted": True,
        "automatic_execution": False,
        "automatic_retry": False,
        "durable_replay_protection": True,
        "source_of_authority": "v32_delegate_service",
    }


def reset_confirmation_consumption_for_tests() -> None:
    reset_v34_execution_audit_for_tests()
    reset_durable_execution_ledger_for_tests()
