import pytest

from src.socmint import database
from src.socmint.durable_execution_ledger_v35_1 import (
    LEDGER_ACTION,
    create_execution,
    execution_snapshot,
    transition_execution,
)
from src.socmint.governance_execution_hardening_v34_8 import RESULT_ACTION
from src.socmint.governance_execution_result_model_v35_3 import (
    GovernanceExecutionResult,
)
from src.socmint.governance_execution_result_service_v35_3 import (
    complete_execution_result,
)
from src.socmint.governance_execution_result_store_v35_3 import (
    ExecutionResultConflict,
    execution_result_snapshot,
)
from src.socmint.human_confirmation_framework_v34_2 import (
    confirmation_identity,
    record_issued_confirmation,
)


def _setup_running(tmp_path, name="result"):
    database.configure_database(
        f"sqlite:///{tmp_path / f'{name}.db'}",
        create_schema=True,
    )
    service = "recall_retention_lifecycle_v32_6.record_retention_decision"
    contract = {
        "status": "confirmation_required",
        "case_id": f"case-{name}",
        "action": "record_retention_decision",
        "delegate_service": service,
        "eligibility_resolution_sha256": f"eligibility-{name}",
        "targets": {},
        "inputs": {
            "disposition": "retain",
            "policy_id": "policy-1",
            "reason": "retention policy applies",
        },
        "impact_summary": (
            f"Confirm record_retention_decision for case case-{name} using "
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
    validation_sha = f"validation-{name}"
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
    return {
        "contract": contract,
        "issuance": issuance,
        "execution": created,
        "running": running,
        "validation_sha": validation_sha,
    }


def _complete_args(setup):
    return {
        "execution_id": setup["execution"]["execution_id"],
        "expected_version": setup["running"]["state_version"],
        "actor": "admin",
        "confirmation_issue_audit_id": setup["issuance"]["audit_record_id"],
        "contract_validation_sha256": setup["validation_sha"],
        "authoritative_record_ids": {
            "audit_record_id": 91,
            "domain_record_id": "record-1",
        },
        "result_reference_sha256": "result-reference-1",
        "workspace_sha256": "workspace-1",
    }


def _counts():
    session = database.Session()
    try:
        return {
            "results": session.query(GovernanceExecutionResult).count(),
            "result_audits": session.query(database.AuditLog)
            .filter_by(action=RESULT_ACTION)
            .count(),
            "ledger_events": session.query(database.AuditLog)
            .filter_by(action=LEDGER_ACTION)
            .count(),
        }
    finally:
        session.close()


def test_v35_3_result_envelope_and_success_transition_are_atomic(tmp_path):
    setup = _setup_running(tmp_path, "success")
    completed = complete_execution_result(**_complete_args(setup))

    assert completed["created"] is True
    assert completed["replay_detected"] is False
    assert completed["execution"]["state"] == "succeeded"
    assert completed["execution"]["state_version"] == 2
    assert completed["execution"]["ledger_consistent"] is True
    assert completed["result"]["final_state"] == "succeeded"
    assert completed["result"]["state_version"] == 2
    assert completed["result"]["result_envelope_sha256"]
    assert completed["result"]["execution_audit_record_id"]
    assert _counts() == {
        "results": 1,
        "result_audits": 1,
        "ledger_events": 3,
    }


def test_v35_3_duplicate_completion_replays_one_result(tmp_path):
    setup = _setup_running(tmp_path, "replay")
    args = _complete_args(setup)
    first = complete_execution_result(**args)
    second = complete_execution_result(**args)

    assert first["created"] is True
    assert second["created"] is False
    assert second["replay_detected"] is True
    assert second["result"]["result_record_id"] == first["result"]["result_record_id"]
    assert _counts() == {
        "results": 1,
        "result_audits": 1,
        "ledger_events": 3,
    }


def test_v35_3_conflicting_duplicate_result_is_rejected(tmp_path):
    setup = _setup_running(tmp_path, "conflict")
    args = _complete_args(setup)
    complete_execution_result(**args)
    args["authoritative_record_ids"] = {"domain_record_id": "different"}

    with pytest.raises(ExecutionResultConflict):
        complete_execution_result(**args)
    assert _counts()["results"] == 1


@pytest.mark.parametrize(
    "point",
    [
        "after_audit_flush",
        "after_envelope_flush",
        "after_state_update",
        "after_ledger_flush",
        "before_commit",
    ],
)
def test_v35_3_precommit_failures_roll_back_all_result_state(tmp_path, point):
    setup = _setup_running(tmp_path, point)

    def fail(selected):
        if selected == point:
            raise RuntimeError(point)

    with pytest.raises(RuntimeError, match=point):
        complete_execution_result(**_complete_args(setup), failure_hook=fail)

    snapshot = execution_snapshot(setup["execution"]["execution_id"])
    assert snapshot is not None
    assert snapshot["state"] == "running"
    assert snapshot["state_version"] == 1
    assert execution_result_snapshot(setup["execution"]["execution_id"]) is None
    assert _counts() == {
        "results": 0,
        "result_audits": 0,
        "ledger_events": 2,
    }


def test_v35_3_postcommit_error_leaves_one_durable_success(tmp_path):
    setup = _setup_running(tmp_path, "postcommit")

    def fail(point):
        if point == "after_commit":
            raise RuntimeError("after_commit")

    with pytest.raises(RuntimeError, match="after_commit"):
        complete_execution_result(
            **_complete_args(setup),
            failure_hook=fail,
        )

    result = execution_result_snapshot(setup["execution"]["execution_id"])
    snapshot = execution_snapshot(setup["execution"]["execution_id"])
    assert result is not None
    assert snapshot is not None
    assert result["final_state"] == "succeeded"
    assert snapshot["state"] == "succeeded"
    assert _counts() == {
        "results": 1,
        "result_audits": 1,
        "ledger_events": 3,
    }
