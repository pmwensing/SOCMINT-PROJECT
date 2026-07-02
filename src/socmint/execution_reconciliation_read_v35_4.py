from __future__ import annotations

import json
from typing import Any

from . import database
from .durable_execution_ledger_v35_1 import (
    GovernanceExecution,
    _snapshot,
)
from .governance_execution_result_model_v35_3 import (
    GovernanceExecutionResult,
    result_row_snapshot,
)
from .governance_execution_result_store_v35_3 import ensure_result_storage

SCHEMA = "socmint.execution_reconciliation_read_model.v35_4"
VERSION = "v35.4.0"


def _details(row: database.AuditLog | None) -> dict[str, Any]:
    if row is None:
        return {}
    try:
        payload = json.loads(row.details or "{}")
    except (TypeError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _execution_payload(session, row: GovernanceExecution) -> dict[str, Any]:
    snapshot = _snapshot(session, row)
    history = list(snapshot.get("history") or [])
    running_event = next(
        (event for event in reversed(history) if event.get("state") == "running"),
        {},
    )
    uncertain_event = next(
        (event for event in reversed(history) if event.get("state") == "uncertain"),
        {},
    )
    running_metadata = running_event.get("metadata") or {}
    uncertain_metadata = uncertain_event.get("metadata") or {}
    if not isinstance(running_metadata, dict):
        running_metadata = {}
    if not isinstance(uncertain_metadata, dict):
        uncertain_metadata = {}

    result_row = (
        session.query(GovernanceExecutionResult)
        .filter_by(execution_id=row.execution_id)
        .first()
    )
    result = result_row_snapshot(result_row) if result_row is not None else None
    operator_metadata: dict[str, Any] = {}
    if result_row is not None:
        result_audit = (
            session.query(database.AuditLog)
            .filter_by(id=result_row.execution_audit_record_id)
            .first()
        )
        audit_details = _details(result_audit)
        raw_operator_metadata = audit_details.get("operator_metadata") or {}
        if isinstance(raw_operator_metadata, dict):
            operator_metadata = raw_operator_metadata

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "execution_record_id": snapshot.get("execution_record_id"),
        "execution_id": row.execution_id,
        "case_id": row.case_id,
        "governance_action": row.governance_action,
        "delegate_service": row.delegate_service,
        "confirmation_sha256": row.confirmation_sha256,
        "state": row.current_state,
        "state_version": row.state_version,
        "last_actor": row.last_actor,
        "last_reason": row.last_reason,
        "created_at": snapshot.get("created_at"),
        "updated_at": snapshot.get("updated_at"),
        "ledger_consistent": snapshot.get("ledger_consistent") is True,
        "history": history,
        "invocation_binding": {
            "ledger_record_id": running_event.get("ledger_record_id"),
            "recorded_at": running_event.get("recorded_at"),
            "confirmation_issue_audit_id": running_metadata.get(
                "confirmation_issue_audit_id"
            ),
            "contract_validation_sha256": running_metadata.get(
                "contract_validation_sha256"
            ),
        },
        "uncertain_outcome": {
            "ledger_record_id": uncertain_event.get("ledger_record_id"),
            "recorded_at": uncertain_event.get("recorded_at"),
            "result_reference_sha256": uncertain_metadata.get(
                "result_reference_sha256"
            ),
            "authoritative_record_ids": uncertain_metadata.get(
                "authoritative_record_ids"
            )
            or {},
            "exception_type": uncertain_metadata.get("exception_type"),
        },
        "result_envelope_exists": result is not None,
        "result_envelope": result,
        "reconciliation_operator_metadata": operator_metadata,
        "automatic_retry": False,
        "delegate_invocation_available": False,
    }


def list_uncertain_executions(
    *,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    ensure_result_storage()
    safe_limit = max(1, min(int(limit), 200))
    safe_offset = max(0, int(offset))
    session = database.Session()
    try:
        total = (
            session.query(GovernanceExecution)
            .filter_by(current_state="uncertain")
            .count()
        )
        rows = (
            session.query(GovernanceExecution)
            .filter_by(current_state="uncertain")
            .order_by(
                GovernanceExecution.updated_at.asc(),
                GovernanceExecution.id.asc(),
            )
            .offset(safe_offset)
            .limit(safe_limit)
            .all()
        )
        executions = [_execution_payload(session, row) for row in rows]
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "status": "ready",
            "state_filter": "uncertain",
            "executions": executions,
            "count": len(executions),
            "total": total,
            "limit": safe_limit,
            "offset": safe_offset,
            "automatic_retry": False,
            "delegate_invocation_available": False,
        }
    finally:
        session.close()


def execution_reconciliation_detail(
    execution_id: str,
) -> dict[str, Any] | None:
    ensure_result_storage()
    normalized = str(execution_id or "").strip()
    if not normalized:
        return None
    session = database.Session()
    try:
        row = (
            session.query(GovernanceExecution)
            .filter_by(execution_id=normalized)
            .first()
        )
        return _execution_payload(session, row) if row is not None else None
    finally:
        session.close()
