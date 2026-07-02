from __future__ import annotations

import json
from typing import Any

from . import database
from .durable_execution_ledger_v35_1 import LEDGER_ACTION, GovernanceExecution
from .governance_execution_result_store_v35_3 import ExecutionResultError
from .human_confirmation_framework_v34_2 import ISSUED_CONFIRMATION_ACTION


def _details(row: database.AuditLog) -> dict[str, Any]:
    try:
        payload = json.loads(row.details or "{}")
    except (TypeError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def verify_result_bindings(
    session,
    execution: GovernanceExecution,
    *,
    confirmation_issue_audit_id: int,
    contract_validation_sha256: str,
) -> dict[str, Any]:
    issue = (
        session.query(database.AuditLog)
        .filter_by(
            id=confirmation_issue_audit_id,
            action=ISSUED_CONFIRMATION_ACTION,
            target_value=execution.confirmation_sha256,
        )
        .first()
    )
    if issue is None:
        raise ExecutionResultError(
            "confirmation issuance audit does not match execution"
        )

    issue_details = _details(issue)
    if any(
        (
            issue_details.get("confirmation_sha256")
            != execution.confirmation_sha256,
            issue_details.get("case_id") != execution.case_id,
            issue_details.get("action") != execution.governance_action,
            issue_details.get("delegate_service")
            != execution.delegate_service,
        )
    ):
        raise ExecutionResultError(
            "confirmation issuance identity does not match execution"
        )

    running_rows = (
        session.query(database.AuditLog)
        .filter_by(action=LEDGER_ACTION, target_value=execution.execution_id)
        .order_by(database.AuditLog.id.desc())
        .all()
    )
    running = next(
        (
            row
            for row in running_rows
            if _details(row).get("state") == "running"
        ),
        None,
    )
    if running is None:
        raise ExecutionResultError("execution has no durable running event")

    running_details = _details(running)
    running_metadata = running_details.get("metadata") or {}
    if not isinstance(running_metadata, dict):
        raise ExecutionResultError("running event metadata is malformed")
    if any(
        (
            running_details.get("execution_id") != execution.execution_id,
            running_details.get("case_id") != execution.case_id,
            running_details.get("governance_action")
            != execution.governance_action,
            running_details.get("confirmation_sha256")
            != execution.confirmation_sha256,
            running_details.get("delegate_service")
            != execution.delegate_service,
        )
    ):
        raise ExecutionResultError(
            "running event identity does not match execution"
        )

    if (
        running_metadata.get("confirmation_issue_audit_id")
        != confirmation_issue_audit_id
    ):
        raise ExecutionResultError(
            "confirmation issuance audit does not match invocation"
        )
    if (
        running_metadata.get("contract_validation_sha256")
        != contract_validation_sha256
    ):
        raise ExecutionResultError(
            "contract validation digest does not match invocation"
        )

    return {
        "confirmation_issue_audit_id": issue.id,
        "confirmation_issue_recorded_at": (
            issue.created_at.isoformat() if issue.created_at else None
        ),
        "running_ledger_record_id": running.id,
        "running_recorded_at": (
            running.created_at.isoformat() if running.created_at else None
        ),
    }
