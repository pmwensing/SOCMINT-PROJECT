import pytest

from src.socmint import database
from src.socmint.durable_execution_ledger_v35_1 import (
    create_execution,
    execution_snapshot,
    transition_execution,
)
from src.socmint.governance_execution_result_service_v35_3 import (
    reconcile_uncertain_execution_result,
)
from src.socmint.governance_execution_result_store_v35_3 import (
    ExecutionResultError,
    execution_result_snapshot,
)
from src.socmint.human_confirmation_framework_v34_2 import (
    confirmation_identity,
    record_issued_confirmation,
)


def _setup_uncertain(tmp_path):
    database.configure_database(
        f"sqlite:///{tmp_path / 'reconcile.db'}",
        create_schema=True,
    )
    service = "delivery_attempt_receipt_ledger_v32_4.record_delivery_attempt"
    contract = {
        "status": "confirmation_required",
        "case_id": "case-reconcile",
        "action": "record_delivery_attempt",
        "delegate_service": service,
        "eligibility_resolution_sha256": "eligibility-reconcile",
        "targets": {"dissemination_package_id": "package-1"},
        "inputs": {
            "recipient_id": "recipient-1",
            "delivery_channel": "secure_portal",
            "endpoint_reference": "reference-1",
            "attempt_result": "accepted",
            "transport_reference": "transport-1",
            "reason": "confirmed delivery attempt",
        },
        "impact_summary": (
            "Confirm record_delivery_attempt for case case-reconcile using "
            f"{service}"
        ),
    }
    identity = confirmation_identity(contract)
    assert identity is not None
    contract["confirmation_id"] = identity["confirmation_id"]
    contract["confirmation_sha256"] = identity["confirmation_sha256"]
    issuance = record_issued_confirmation(contract, "admin")
    assert issuance["issued"] is True

    created = create_execution(
        confirmation_sha256=contract["confirmation_sha256"],
        actor="admin",
        case_id=contract["case_id"],
        governance_action=contract["action"],
        delegate_service=service,
    )
    validation_sha = "validation-reconcile"
    running = transition_execution(
        execution_id=created["execution_id"],
        expected_state="pending",
        expected_version=created["state_version"],
        new_state="running",
        actor="admin",
        reason="authoritative_delegate_invocation_started",
        metadata={
            "contract_validation_sha256": validation_sha,
            "confirmation_issue_audit_id": issuance["audit_record_id"],
        },
    )
    uncertain = transition_execution(
        execution_id=created["execution_id"],
        expected_state="running",
        expected_version=running["state_version"],
        new_state="uncertain",
        actor="admin",
        reason="delegate_result_atomic_commit_failed",
        metadata={
            "result_reference_sha256": "result-reference-reconcile",
            "authoritative_record_ids": {"delivery_attempt_id": "attempt-1"},
        },
    )
    return {
        "execution": created,
        "uncertain": uncertain,
        "issuance": issuance,
        "validation_sha": validation_sha,
    }


def _reconcile_args(setup):
    return {
        "execution_id": setup["execution"]["execution_id"],
        "expected_version": setup["uncertain"]["state_version"],
        "actor": "supervisor",
        "confirmation_issue_audit_id": setup["issuance"]["audit_record_id"],
        "contract_validation_sha256": setup["validation_sha"],
        "authoritative_record_ids": {"delivery_attempt_id": "attempt-1"},
        "result_reference_sha256": "result-reference-reconcile",
        "workspace_sha256": "workspace-reconcile",
    }


def test_v35_3_uncertain_result_reconciles_without_delegate_call(tmp_path):
    setup = _setup_uncertain(tmp_path)
    calls = []

    result = reconcile_uncertain_execution_result(**_reconcile_args(setup))

    assert calls == []
    assert result["created"] is True
    assert result["execution"]["state"] == "reconciled"
    assert result["execution"]["state_version"] == 3
    assert result["result"]["final_state"] == "reconciled"
    assert result["result"]["authoritative_record_ids"] == {
        "delivery_attempt_id": "attempt-1"
    }
    snapshot = execution_snapshot(setup["execution"]["execution_id"])
    envelope = execution_result_snapshot(setup["execution"]["execution_id"])
    assert snapshot is not None and snapshot["state"] == "reconciled"
    assert envelope is not None and envelope["final_state"] == "reconciled"


def test_v35_3_reconciliation_is_idempotent(tmp_path):
    setup = _setup_uncertain(tmp_path)
    args = _reconcile_args(setup)
    first = reconcile_uncertain_execution_result(**args)
    second = reconcile_uncertain_execution_result(**args)

    assert first["created"] is True
    assert second["created"] is False
    assert second["replay_detected"] is True
    assert second["result"]["result_record_id"] == first["result"]["result_record_id"]


def test_v35_3_reconciliation_rejects_wrong_validation_binding(tmp_path):
    setup = _setup_uncertain(tmp_path)
    args = _reconcile_args(setup)
    args["contract_validation_sha256"] = "wrong-validation"

    with pytest.raises(
        ExecutionResultError,
        match="contract validation digest does not match invocation",
    ):
        reconcile_uncertain_execution_result(**args)
    assert execution_result_snapshot(setup["execution"]["execution_id"]) is None


def test_v35_3_reconciliation_rejects_wrong_issuance_binding(tmp_path):
    setup = _setup_uncertain(tmp_path)
    args = _reconcile_args(setup)
    args["confirmation_issue_audit_id"] += 999

    with pytest.raises(
        ExecutionResultError,
        match="confirmation issuance audit does not match execution",
    ):
        reconcile_uncertain_execution_result(**args)
    assert execution_result_snapshot(setup["execution"]["execution_id"]) is None
