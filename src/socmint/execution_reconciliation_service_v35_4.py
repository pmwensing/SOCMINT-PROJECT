from __future__ import annotations

from typing import Any

from .durable_execution_ledger_v35_1 import (
    ExecutionNotFound,
    ExecutionStateConflict,
)
from .execution_reconciliation_contract_v35_4 import (
    VERSION,
    validate_reconciliation_request,
)
from .execution_reconciliation_read_v35_4 import (
    execution_reconciliation_detail,
)
from .governance_execution_result_service_v35_3 import (
    reconcile_uncertain_execution_result,
)
from .governance_execution_result_store_v35_3 import ExecutionResultError

SCHEMA = "socmint.execution_reconciliation_service.v35_4"


class ReconciliationBindingError(ExecutionResultError):
    """Raised when durable invocation bindings are unavailable."""


def reconcile_execution(
    execution_id: str,
    request_payload: Any,
    *,
    actor: str,
) -> dict[str, Any]:
    validation = validate_reconciliation_request(request_payload)
    if validation.get("valid") is not True:
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "status": "invalid_request",
            "execution_id": str(execution_id or ""),
            "request_validation": validation,
            "execution_performed": False,
            "delegate_invoked": False,
            "automatic_retry": False,
        }

    detail = execution_reconciliation_detail(execution_id)
    if detail is None:
        raise ExecutionNotFound(str(execution_id or ""))
    normalized = validation["normalized"]
    if detail.get("state") != "uncertain":
        raise ExecutionStateConflict(
            f"expected uncertain, durable state is {detail.get('state')}"
        )
    if int(detail.get("state_version") or -1) != int(
        normalized["expected_version"]
    ):
        raise ExecutionStateConflict(
            "expected version does not match durable execution version"
        )

    invocation_binding = detail.get("invocation_binding") or {}
    confirmation_issue_audit_id = invocation_binding.get(
        "confirmation_issue_audit_id"
    )
    contract_validation_sha256 = invocation_binding.get(
        "contract_validation_sha256"
    )
    if not confirmation_issue_audit_id or not contract_validation_sha256:
        raise ReconciliationBindingError(
            "durable invocation bindings are incomplete"
        )

    operator_metadata = {
        "schema": SCHEMA,
        "version": VERSION,
        "reconciliation_reason": normalized["reconciliation_reason"],
        "evidence_references": normalized["evidence_references"],
        "request_validation_sha256": validation["validation_sha256"],
        "actor": str(actor or ""),
        "delegate_invoked": False,
        "automatic_retry": False,
    }
    result = reconcile_uncertain_execution_result(
        execution_id=str(execution_id),
        expected_version=int(normalized["expected_version"]),
        actor=str(actor or ""),
        confirmation_issue_audit_id=int(confirmation_issue_audit_id),
        contract_validation_sha256=str(contract_validation_sha256),
        authoritative_record_ids=normalized["authoritative_record_ids"],
        result_reference_sha256=normalized["result_reference_sha256"],
        workspace_sha256=normalized["workspace_sha256"],
        operator_metadata=operator_metadata,
    )
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "reconciled",
        "execution_id": str(execution_id),
        "request_validation": {
            "schema": validation["schema"],
            "version": validation["version"],
            "valid": True,
            "errors": [],
            "validation_sha256": validation["validation_sha256"],
        },
        "reconciliation": result,
        "execution_performed": True,
        "delegate_invoked": False,
        "automatic_retry": False,
    }
