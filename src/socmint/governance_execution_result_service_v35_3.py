from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from . import database
from .durable_execution_ledger_v35_1 import ExecutionNotFound, GovernanceExecution
from .governance_execution_result_binding_v35_3 import verify_result_bindings
from .governance_execution_result_transition_v35_3 import (
    complete_execution_result as persist_completed_result,
    reconcile_uncertain_execution_result as persist_reconciled_result,
    reset_execution_results_for_tests,
)


def _verify(
    execution_id: str,
    confirmation_issue_audit_id: int,
    contract_validation_sha256: str,
) -> None:
    database.ensure_configured()
    session = database.Session()
    try:
        execution = (
            session.query(GovernanceExecution)
            .filter_by(execution_id=execution_id)
            .first()
        )
        if execution is None:
            raise ExecutionNotFound(execution_id)
        verify_result_bindings(
            session,
            execution,
            confirmation_issue_audit_id=confirmation_issue_audit_id,
            contract_validation_sha256=contract_validation_sha256,
        )
    finally:
        session.close()


def complete_execution_result(
    *,
    execution_id: str,
    expected_version: int,
    actor: str,
    confirmation_issue_audit_id: int,
    contract_validation_sha256: str,
    authoritative_record_ids: Mapping[str, Any],
    result_reference_sha256: str,
    workspace_sha256: str,
    failure_hook=None,
) -> dict[str, Any]:
    _verify(
        execution_id,
        confirmation_issue_audit_id,
        contract_validation_sha256,
    )
    return persist_completed_result(
        execution_id=execution_id,
        expected_version=expected_version,
        actor=actor,
        confirmation_issue_audit_id=confirmation_issue_audit_id,
        contract_validation_sha256=contract_validation_sha256,
        authoritative_record_ids=authoritative_record_ids,
        result_reference_sha256=result_reference_sha256,
        workspace_sha256=workspace_sha256,
        failure_hook=failure_hook,
    )


def reconcile_uncertain_execution_result(
    *,
    execution_id: str,
    expected_version: int,
    actor: str,
    confirmation_issue_audit_id: int,
    contract_validation_sha256: str,
    authoritative_record_ids: Mapping[str, Any],
    result_reference_sha256: str,
    workspace_sha256: str,
    failure_hook=None,
) -> dict[str, Any]:
    _verify(
        execution_id,
        confirmation_issue_audit_id,
        contract_validation_sha256,
    )
    return persist_reconciled_result(
        execution_id=execution_id,
        expected_version=expected_version,
        actor=actor,
        confirmation_issue_audit_id=confirmation_issue_audit_id,
        contract_validation_sha256=contract_validation_sha256,
        authoritative_record_ids=authoritative_record_ids,
        result_reference_sha256=result_reference_sha256,
        workspace_sha256=workspace_sha256,
        failure_hook=failure_hook,
    )
