from src.socmint import database
from src.socmint.governance_action_execution_v34_3_6 import (
    execute_confirmed_action,
    reset_confirmation_consumption_for_tests,
)
from src.socmint.governance_execution_result_store_v35_3 import (
    execution_result_snapshot,
)
from src.socmint.governance_execution_result_transition_v35_3 import (
    complete_execution_result as persist_completed_result,
)
from src.socmint.human_confirmation_framework_v34_2 import (
    confirmation_identity,
    record_issued_confirmation,
)


def _contract():
    service = "recall_retention_lifecycle_v32_6.record_retention_decision"
    contract = {
        "status": "confirmation_required",
        "case_id": "case-crash",
        "action": "record_retention_decision",
        "delegate_service": service,
        "eligibility_resolution_sha256": "eligibility-crash",
        "targets": {},
        "inputs": {
            "disposition": "retain",
            "policy_id": "policy-1",
            "reason": "retention policy applies",
        },
        "impact_summary": (
            "Confirm record_retention_decision for case case-crash using "
            f"{service}"
        ),
    }
    identity = confirmation_identity(contract)
    assert identity is not None
    contract["confirmation_id"] = identity["confirmation_id"]
    contract["confirmation_sha256"] = identity["confirmation_sha256"]
    issuance = record_issued_confirmation(contract, "admin")
    assert issuance["issued"] is True
    return contract


def test_precommit_failure_becomes_uncertain_without_delegate_retry(
    monkeypatch,
    tmp_path,
):
    database.configure_database(
        f"sqlite:///{tmp_path / 'precommit-integration.db'}",
        create_schema=True,
    )
    reset_confirmation_consumption_for_tests()
    contract = _contract()
    service = contract["delegate_service"]
    calls = []

    def delegate(**kwargs):
        calls.append(kwargs)
        return {"retention_decision_id": "decision-1"}

    def fail(point):
        if point == "before_commit":
            raise RuntimeError("before_commit")

    def complete_with_failure(**kwargs):
        return persist_completed_result(**kwargs, failure_hook=fail)

    monkeypatch.setattr(
        "src.socmint.governance_action_execution_v34_3_6.complete_execution_result",
        complete_with_failure,
    )
    monkeypatch.setattr(
        "src.socmint.governance_action_execution_v34_3_6.refreshed_workspace",
        lambda case_id: {"case_id": case_id, "workspace_sha256": "workspace-crash"},
    )

    first = execute_confirmed_action(
        contract,
        contract["confirmation_id"],
        True,
        "admin",
        {service: delegate},
    )
    second = execute_confirmed_action(
        contract,
        contract["confirmation_id"],
        True,
        "admin",
        {service: delegate},
    )

    assert first["status"] == "uncertain"
    assert first["execution_state"] == "uncertain"
    assert first["automatic_retry"] is False
    assert second["status"] == "duplicate_rejected"
    assert len(calls) == 1
    assert execution_result_snapshot(first["execution_id"]) is None


def test_postcommit_error_is_recovered_as_success_without_delegate_retry(
    monkeypatch,
    tmp_path,
):
    database.configure_database(
        f"sqlite:///{tmp_path / 'postcommit-integration.db'}",
        create_schema=True,
    )
    reset_confirmation_consumption_for_tests()
    contract = _contract()
    service = contract["delegate_service"]
    calls = []

    def delegate(**kwargs):
        calls.append(kwargs)
        return {"retention_decision_id": "decision-1"}

    def fail(point):
        if point == "after_commit":
            raise RuntimeError("after_commit")

    def complete_with_failure(**kwargs):
        return persist_completed_result(**kwargs, failure_hook=fail)

    monkeypatch.setattr(
        "src.socmint.governance_action_execution_v34_3_6.complete_execution_result",
        complete_with_failure,
    )
    monkeypatch.setattr(
        "src.socmint.governance_action_execution_v34_3_6.refreshed_workspace",
        lambda case_id: {"case_id": case_id, "workspace_sha256": "workspace-crash"},
    )

    first = execute_confirmed_action(
        contract,
        contract["confirmation_id"],
        True,
        "admin",
        {service: delegate},
    )
    second = execute_confirmed_action(
        contract,
        contract["confirmation_id"],
        True,
        "admin",
        {service: delegate},
    )

    assert first["status"] == "executed"
    assert first["execution_state"] == "succeeded"
    assert first["result_replay_detected"] is True
    assert second["status"] == "duplicate_rejected"
    assert len(calls) == 1
    envelope = execution_result_snapshot(first["execution_id"])
    assert envelope is not None
    assert envelope["final_state"] == "succeeded"
