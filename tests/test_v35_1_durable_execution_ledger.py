import pytest

from src.socmint import database
from src.socmint.durable_execution_ledger_v35_1 import (
    ExecutionStateConflict,
    InvalidExecutionTransition,
    create_execution,
    execution_snapshot,
    reset_execution_ledger_for_tests,
    transition_execution,
)


def _configure(tmp_path):
    database.configure_database(
        f"sqlite:///{tmp_path / 'socmint-v35-1.db'}", create_schema=True
    )
    reset_execution_ledger_for_tests()


def _create():
    return create_execution(
        confirmation_sha256="a" * 64,
        actor="operator@example.test",
        case_id="case-v35-1",
        governance_action="record_delivery_attempt",
        delegate_service="delivery_attempt_receipt_ledger_v32_4.record_delivery_attempt",
    )


def test_v35_1_creates_pending_execution_and_rejects_replay(tmp_path):
    _configure(tmp_path)

    created = _create()
    replay = _create()

    assert created["created"] is True
    assert created["state"] == "pending"
    assert created["event_count"] == 1
    assert replay["created"] is False
    assert replay["replay_detected"] is True
    assert replay["execution_id"] == created["execution_id"]
    assert replay["event_count"] == 1
    assert replay["automatic_retry"] is False


def test_v35_1_persists_state_across_database_reconfiguration(tmp_path):
    _configure(tmp_path)
    created = _create()

    database.configure_database(
        f"sqlite:///{tmp_path / 'socmint-v35-1.db'}", create_schema=False
    )
    restored = execution_snapshot(created["execution_id"])

    assert restored is not None
    assert restored["state"] == "pending"
    assert restored["history"][0]["reason"] == "confirmed_action_accepted"


def test_v35_1_supports_only_the_canonical_forward_state_path(tmp_path):
    _configure(tmp_path)
    created = _create()

    running = transition_execution(
        execution_id=created["execution_id"],
        expected_state="pending",
        new_state="running",
        actor="operator@example.test",
        reason="authoritative_delegate_invoked",
    )
    succeeded = transition_execution(
        execution_id=created["execution_id"],
        expected_state="running",
        new_state="succeeded",
        actor="operator@example.test",
        reason="authoritative_delegate_succeeded",
        metadata={"authoritative_record_id": "delivery-123"},
    )
    reconciled = transition_execution(
        execution_id=created["execution_id"],
        expected_state="succeeded",
        new_state="reconciled",
        actor="reviewer@example.test",
        reason="workspace_and_authoritative_records_match",
    )

    assert running["state"] == "running"
    assert succeeded["state"] == "succeeded"
    assert reconciled["state"] == "reconciled"
    assert reconciled["event_count"] == 4
    assert all(event["automatic_retry"] is False for event in reconciled["history"])


def test_v35_1_rejects_stale_expected_state_and_backward_replay(tmp_path):
    _configure(tmp_path)
    created = _create()
    transition_execution(
        execution_id=created["execution_id"],
        expected_state="pending",
        new_state="running",
        actor="operator@example.test",
        reason="authoritative_delegate_invoked",
    )

    with pytest.raises(ExecutionStateConflict):
        transition_execution(
            execution_id=created["execution_id"],
            expected_state="pending",
            new_state="failed",
            actor="operator@example.test",
            reason="stale_worker_result",
        )

    with pytest.raises(InvalidExecutionTransition):
        transition_execution(
            execution_id=created["execution_id"],
            expected_state="running",
            new_state="pending",
            actor="operator@example.test",
            reason="automatic_retry_attempt",
        )


def test_v35_1_failed_and_uncertain_states_cannot_retry_automatically(tmp_path):
    _configure(tmp_path)
    failed = _create()
    transition_execution(
        execution_id=failed["execution_id"],
        expected_state="pending",
        new_state="failed",
        actor="operator@example.test",
        reason="delegate_rejected_input",
    )

    with pytest.raises(InvalidExecutionTransition):
        transition_execution(
            execution_id=failed["execution_id"],
            expected_state="failed",
            new_state="running",
            actor="operator@example.test",
            reason="unreviewed_retry",
        )

    uncertain = create_execution(
        confirmation_sha256="b" * 64,
        actor="operator@example.test",
        case_id="case-v35-1",
        governance_action="record_delivery_receipt",
        delegate_service="delivery_attempt_receipt_ledger_v32_4.record_delivery_receipt",
    )
    transition_execution(
        execution_id=uncertain["execution_id"],
        expected_state="pending",
        new_state="uncertain",
        actor="operator@example.test",
        reason="delegate_result_not_confirmed",
    )

    with pytest.raises(InvalidExecutionTransition):
        transition_execution(
            execution_id=uncertain["execution_id"],
            expected_state="uncertain",
            new_state="running",
            actor="operator@example.test",
            reason="silent_replay",
        )
