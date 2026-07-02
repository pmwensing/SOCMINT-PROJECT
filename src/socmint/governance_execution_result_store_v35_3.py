from __future__ import annotations

import json
from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from . import database
from .durable_execution_ledger_v35_1 import (
    ExecutionNotFound,
    GovernanceExecution,
    _snapshot,
)
from .governance_execution_result_model_v35_3 import (
    GovernanceExecutionResult,
    decode_record_ids,
    result_row_snapshot,
)


class ExecutionResultError(ValueError):
    """Base error for durable execution-result operations."""


class ExecutionResultConflict(ExecutionResultError):
    """Raised when an execution already has a different result."""


def required_text(value: Any, field: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ExecutionResultError(f"{field} is required")
    return normalized


def positive_integer(value: Any, field: str) -> int:
    try:
        normalized = int(value)
    except (TypeError, ValueError) as exc:
        raise ExecutionResultError(f"{field} must be an integer") from exc
    if normalized <= 0:
        raise ExecutionResultError(f"{field} must be positive")
    return normalized


def normalized_record_ids(
    value: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ExecutionResultError(
            "authoritative_record_ids must be a mapping"
        )
    normalized = {
        str(key): deepcopy(item)
        for key, item in value.items()
        if str(key).strip() and item not in (None, "")
    }
    if not normalized:
        raise ExecutionResultError("authoritative_record_ids are required")
    return normalized


def ensure_result_storage() -> None:
    database.ensure_configured()
    database.AuditLog.__table__.create(bind=database.engine, checkfirst=True)
    GovernanceExecution.__table__.create(bind=database.engine, checkfirst=True)
    GovernanceExecutionResult.__table__.create(
        bind=database.engine,
        checkfirst=True,
    )


def execution_result_snapshot(
    execution_id: str,
) -> dict[str, Any] | None:
    ensure_result_storage()
    session = database.Session()
    try:
        row = (
            session.query(GovernanceExecutionResult)
            .filter_by(execution_id=required_text(execution_id, "execution_id"))
            .first()
        )
        return result_row_snapshot(row) if row is not None else None
    finally:
        session.close()


def same_result(
    existing: GovernanceExecutionResult,
    *,
    confirmation_sha256: str,
    confirmation_issue_audit_id: int,
    contract_validation_sha256: str,
    case_id: str,
    governance_action: str,
    delegate_service: str,
    authoritative_record_ids: dict[str, Any],
    result_reference_sha256: str,
    final_state: str,
    workspace_sha256: str,
) -> bool:
    return all(
        (
            existing.confirmation_sha256 == confirmation_sha256,
            existing.confirmation_issue_audit_id
            == confirmation_issue_audit_id,
            existing.contract_validation_sha256
            == contract_validation_sha256,
            existing.case_id == case_id,
            existing.governance_action == governance_action,
            existing.delegate_service == delegate_service,
            decode_record_ids(existing.authoritative_record_ids)
            == authoritative_record_ids,
            existing.result_reference_sha256 == result_reference_sha256,
            existing.final_state == final_state,
            existing.workspace_sha256 == workspace_sha256,
        )
    )


def _audit_details(row: database.AuditLog | None) -> dict[str, Any]:
    if row is None:
        return {}
    try:
        payload = json.loads(row.details or "{}")
    except (TypeError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def existing_result_response(
    session,
    existing: GovernanceExecutionResult,
    **expected: Any,
) -> dict[str, Any]:
    expected_operator_metadata = expected.pop("operator_metadata", {}) or {}
    if not same_result(existing, **expected):
        raise ExecutionResultConflict(
            "execution already has a different authoritative result"
        )
    audit_row = (
        session.query(database.AuditLog)
        .filter_by(id=existing.execution_audit_record_id)
        .first()
    )
    audit_details = _audit_details(audit_row)
    stored_operator_metadata = audit_details.get("operator_metadata") or {}
    if stored_operator_metadata != expected_operator_metadata:
        raise ExecutionResultConflict(
            "execution already has different reconciliation evidence"
        )
    execution = (
        session.query(GovernanceExecution)
        .filter_by(execution_id=existing.execution_id)
        .first()
    )
    if execution is None:
        raise ExecutionNotFound(existing.execution_id)
    return {
        "created": False,
        "replay_detected": True,
        "result": result_row_snapshot(existing),
        "execution": _snapshot(session, execution),
        "execution_audit": {
            "audit_record_id": existing.execution_audit_record_id,
            "recorded_at": (
                existing.recorded_at.isoformat()
                if existing.recorded_at
                else None
            ),
            "operator_metadata": stored_operator_metadata,
        },
    }
