from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from sqlalchemy.exc import IntegrityError

from . import database
from .dossier_assembly_workspace_v21_0 import _canonical, _sha
from .durable_execution_ledger_v35_1 import (
    ALLOWED_TRANSITIONS,
    EXECUTION_STATES,
    LEDGER_ACTION,
    ExecutionNotFound,
    ExecutionStateConflict,
    GovernanceExecution,
    InvalidExecutionTransition,
    _snapshot,
    _transition_statement,
)
from .governance_execution_hardening_v34_8 import RESULT_ACTION
from .governance_execution_result_model_v35_3 import (
    RESULT_IDENTITY_SCHEMA,
    VERSION,
    GovernanceExecutionResult,
    result_row_snapshot,
)
from .governance_execution_result_store_v35_3 import (
    ExecutionResultError,
    ensure_result_storage,
    existing_result_response,
    normalized_record_ids,
    positive_integer,
    required_text,
)

FailureHook = Callable[[str], None]


def _checkpoint(hook: FailureHook | None, point: str) -> None:
    if hook is not None:
        hook(point)


def _persist_result_transition(
    *,
    execution_id: str,
    expected_state: str,
    expected_version: int,
    final_state: str,
    actor: str,
    reason: str,
    confirmation_issue_audit_id: int,
    contract_validation_sha256: str,
    authoritative_record_ids: Mapping[str, Any],
    result_reference_sha256: str,
    workspace_sha256: str,
    failure_hook: FailureHook | None = None,
) -> dict[str, Any]:
    execution_id = required_text(execution_id, "execution_id")
    expected_state = required_text(expected_state, "expected_state")
    final_state = required_text(final_state, "final_state")
    actor = required_text(actor, "actor")
    reason = required_text(reason, "reason")
    confirmation_issue_audit_id = positive_integer(
        confirmation_issue_audit_id,
        "confirmation_issue_audit_id",
    )
    contract_validation_sha256 = required_text(
        contract_validation_sha256,
        "contract_validation_sha256",
    )
    result_reference_sha256 = required_text(
        result_reference_sha256,
        "result_reference_sha256",
    )
    workspace_sha256 = required_text(workspace_sha256, "workspace_sha256")
    record_ids = normalized_record_ids(authoritative_record_ids)

    if expected_state not in EXECUTION_STATES:
        raise InvalidExecutionTransition(f"unknown expected state: {expected_state}")
    if final_state not in EXECUTION_STATES:
        raise InvalidExecutionTransition(f"unknown final state: {final_state}")
    if final_state not in ALLOWED_TRANSITIONS[expected_state]:
        raise InvalidExecutionTransition(
            f"transition {expected_state} -> {final_state} is not allowed"
        )

    ensure_result_storage()
    session = database.Session()
    expected: dict[str, Any] | None = None
    try:
        execution = (
            session.query(GovernanceExecution)
            .filter_by(execution_id=execution_id)
            .first()
        )
        if execution is None:
            raise ExecutionNotFound(execution_id)

        expected = {
            "confirmation_sha256": execution.confirmation_sha256,
            "confirmation_issue_audit_id": confirmation_issue_audit_id,
            "contract_validation_sha256": contract_validation_sha256,
            "case_id": execution.case_id,
            "governance_action": execution.governance_action,
            "delegate_service": execution.delegate_service,
            "authoritative_record_ids": record_ids,
            "result_reference_sha256": result_reference_sha256,
            "final_state": final_state,
            "workspace_sha256": workspace_sha256,
        }
        existing = (
            session.query(GovernanceExecutionResult)
            .filter_by(execution_id=execution_id)
            .first()
        )
        if existing is not None:
            return existing_result_response(session, existing, **expected)

        if execution.current_state != expected_state:
            raise ExecutionStateConflict(
                f"expected {expected_state}, durable state is "
                f"{execution.current_state}"
            )
        durable_version = int(execution.state_version)
        if int(expected_version) != durable_version:
            raise ExecutionStateConflict(
                f"expected version {expected_version}, durable version is "
                f"{durable_version}"
            )
        next_version = durable_version + 1
        recorded_at = database.utc_now()

        execution_audit = database.AuditLog(
            actor=actor,
            action=RESULT_ACTION,
            target_value=execution.case_id,
            details="{}",
            created_at=recorded_at,
        )
        session.add(execution_audit)
        session.flush()
        _checkpoint(failure_hook, "after_audit_flush")

        envelope_content = {
            "schema": RESULT_IDENTITY_SCHEMA,
            "version": VERSION,
            "execution_id": execution.execution_id,
            "confirmation_sha256": execution.confirmation_sha256,
            "confirmation_issue_audit_id": confirmation_issue_audit_id,
            "contract_validation_sha256": contract_validation_sha256,
            "case_id": execution.case_id,
            "governance_action": execution.governance_action,
            "delegate_service": execution.delegate_service,
            "authoritative_record_ids": record_ids,
            "result_reference_sha256": result_reference_sha256,
            "final_state": final_state,
            "state_version": next_version,
            "workspace_sha256": workspace_sha256,
            "actor": actor,
            "execution_audit_record_id": execution_audit.id,
            "recorded_at": recorded_at.isoformat(),
        }
        envelope_sha256 = _sha(envelope_content)
        execution_audit.details = _canonical(
            {
                **envelope_content,
                "result_envelope_sha256": envelope_sha256,
                "atomic_result_completion": True,
                "automatic_retry": False,
            }
        )

        result_row = GovernanceExecutionResult(
            execution_id=execution.execution_id,
            confirmation_sha256=execution.confirmation_sha256,
            confirmation_issue_audit_id=confirmation_issue_audit_id,
            contract_validation_sha256=contract_validation_sha256,
            case_id=execution.case_id,
            governance_action=execution.governance_action,
            delegate_service=execution.delegate_service,
            authoritative_record_ids=_canonical(record_ids),
            result_reference_sha256=result_reference_sha256,
            final_state=final_state,
            state_version=next_version,
            workspace_sha256=workspace_sha256,
            actor=actor,
            execution_audit_record_id=execution_audit.id,
            recorded_at=recorded_at,
            result_envelope_sha256=envelope_sha256,
        )
        session.add(result_row)
        session.flush()
        _checkpoint(failure_hook, "after_envelope_flush")

        changed = session.execute(
            _transition_statement(
                execution_id=execution.execution_id,
                expected_state=expected_state,
                expected_version=durable_version,
                new_state=final_state,
                actor=actor,
                reason=reason,
            )
        )
        if changed.rowcount != 1:
            raise ExecutionStateConflict(
                "durable execution state changed before atomic result commit"
            )
        _checkpoint(failure_hook, "after_state_update")

        ledger_event = database.AuditLog(
            actor=actor,
            action=LEDGER_ACTION,
            target_value=execution.execution_id,
            details=_canonical(
                {
                    "schema": RESULT_IDENTITY_SCHEMA,
                    "version": VERSION,
                    "event_type": "execution_result_committed",
                    "execution_id": execution.execution_id,
                    "case_id": execution.case_id,
                    "governance_action": execution.governance_action,
                    "confirmation_sha256": execution.confirmation_sha256,
                    "delegate_service": execution.delegate_service,
                    "previous_state": expected_state,
                    "state": final_state,
                    "state_version": next_version,
                    "reason": reason,
                    "metadata": {
                        "result_record_id": result_row.id,
                        "result_envelope_sha256": envelope_sha256,
                        "execution_audit_record_id": execution_audit.id,
                        "authoritative_record_ids": record_ids,
                        "result_reference_sha256": result_reference_sha256,
                        "workspace_sha256": workspace_sha256,
                    },
                    "automatic_retry": False,
                    "retry_authorized": False,
                }
            ),
            created_at=recorded_at,
        )
        session.add(ledger_event)
        session.flush()
        _checkpoint(failure_hook, "after_ledger_flush")
        _checkpoint(failure_hook, "before_commit")
        session.commit()
        _checkpoint(failure_hook, "after_commit")

        execution = (
            session.query(GovernanceExecution)
            .filter_by(execution_id=execution_id)
            .first()
        )
        result_row = (
            session.query(GovernanceExecutionResult)
            .filter_by(execution_id=execution_id)
            .first()
        )
        if execution is None or result_row is None:
            raise ExecutionResultError("atomic result commit was not durable")
        return {
            "created": True,
            "replay_detected": False,
            "result": result_row_snapshot(result_row),
            "execution": _snapshot(session, execution),
            "execution_audit": {
                "audit_record_id": execution_audit.id,
                "recorded_at": recorded_at.isoformat(),
            },
            "ledger_record_id": ledger_event.id,
        }
    except IntegrityError:
        session.rollback()
        if expected is None:
            raise
        existing = (
            session.query(GovernanceExecutionResult)
            .filter_by(execution_id=execution_id)
            .first()
        )
        if existing is None:
            raise
        return existing_result_response(session, existing, **expected)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def complete_execution_result(**kwargs: Any) -> dict[str, Any]:
    return _persist_result_transition(
        expected_state="running",
        final_state="succeeded",
        reason="authoritative_delegate_result_atomically_persisted",
        **kwargs,
    )


def reconcile_uncertain_execution_result(**kwargs: Any) -> dict[str, Any]:
    return _persist_result_transition(
        expected_state="uncertain",
        final_state="reconciled",
        reason="authoritative_result_reconciled_without_delegate_retry",
        **kwargs,
    )


def reset_execution_results_for_tests() -> None:
    ensure_result_storage()
    session = database.Session()
    try:
        session.query(GovernanceExecutionResult).delete(synchronize_session=False)
        session.query(database.AuditLog).filter_by(action=RESULT_ACTION).delete(
            synchronize_session=False
        )
        session.commit()
    finally:
        session.close()
