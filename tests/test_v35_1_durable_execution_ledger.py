import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy.dialects import postgresql, sqlite

from src.socmint import database
from src.socmint.durable_execution_ledger_v35_1 import (
    ExecutionStateConflict,
    InvalidExecutionTransition,
    _transition_statement,
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


def _create(digest="a" * 64):
    return create_execution(
        confirmation_sha256=digest,
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
    assert created["state_version"] == 0
    assert created["event_count"] == 1
    assert created["ledger_consistent"] is True
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
    assert restored["state_version"] == 0
    assert restored["history"][0]["reason"] == "confirmed_action_accepted"
    assert restored["ledger_consistent"] is True


def test_v35_1_supports_only_the_canonical_forward_state_path(tmp_path):
    _configure(tmp_path)
    created = _create()

    running = transition_execution(
        execution_id=created["execution_id"],
        expected_state="pending",
        expected_version=created["state_version"],
        new_state="running",
        actor="operator@example.test",
        reason="authoritative_delegate_invoked",
    )
    succeeded = transition_execution(
        execution_id=created["execution_id"],
        expected_state="running",
        expected_version=running["state_version"],
        new_state="succeeded",
        actor="operator@example.test",
        reason="authoritative_delegate_succeeded",
        metadata={"authoritative_record_id": "delivery-123"},
    )
    reconciled = transition_execution(
        execution_id=created["execution_id"],
        expected_state="succeeded",
        expected_version=succeeded["state_version"],
        new_state="reconciled",
        actor="reviewer@example.test",
        reason="workspace_and_authoritative_records_match",
    )

    assert running["state"] == "running"
    assert running["state_version"] == 1
    assert succeeded["state"] == "succeeded"
    assert succeeded["state_version"] == 2
    assert reconciled["state"] == "reconciled"
    assert reconciled["state_version"] == 3
    assert reconciled["event_count"] == 4
    assert reconciled["ledger_consistent"] is True
    assert all(event["automatic_retry"] is False for event in reconciled["history"])


def test_v35_1_rejects_stale_expected_state_and_backward_replay(tmp_path):
    _configure(tmp_path)
    created = _create()
    transition_execution(
        execution_id=created["execution_id"],
        expected_state="pending",
        expected_version=0,
        new_state="running",
        actor="operator@example.test",
        reason="authoritative_delegate_invoked",
    )

    with pytest.raises(ExecutionStateConflict):
        transition_execution(
            execution_id=created["execution_id"],
            expected_state="pending",
            expected_version=0,
            new_state="failed",
            actor="operator@example.test",
            reason="stale_worker_result",
        )

    with pytest.raises(InvalidExecutionTransition):
        transition_execution(
            execution_id=created["execution_id"],
            expected_state="running",
            expected_version=1,
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
        expected_version=0,
        new_state="failed",
        actor="operator@example.test",
        reason="delegate_rejected_input",
    )

    with pytest.raises(InvalidExecutionTransition):
        transition_execution(
            execution_id=failed["execution_id"],
            expected_state="failed",
            expected_version=1,
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
        expected_version=0,
        new_state="uncertain",
        actor="operator@example.test",
        reason="delegate_result_not_confirmed",
    )

    with pytest.raises(InvalidExecutionTransition):
        transition_execution(
            execution_id=uncertain["execution_id"],
            expected_state="uncertain",
            expected_version=1,
            new_state="running",
            actor="operator@example.test",
            reason="silent_replay",
        )


def test_v35_1_two_simultaneous_creates_produce_one_execution(tmp_path):
    _configure(tmp_path)
    barrier = Barrier(2)

    def worker():
        barrier.wait()
        return _create()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: worker(), range(2)))

    assert sum(result["created"] is True for result in results) == 1
    assert sum(result["replay_detected"] is True for result in results) == 1
    assert len({result["execution_id"] for result in results}) == 1
    snapshot = execution_snapshot(results[0]["execution_id"])
    assert snapshot is not None
    assert snapshot["event_count"] == 1
    assert snapshot["state"] == "pending"


def test_v35_1_two_workers_cannot_commit_conflicting_transitions(tmp_path):
    _configure(tmp_path)
    created = _create()
    barrier = Barrier(2)

    def worker(new_state):
        barrier.wait()
        try:
            value = transition_execution(
                execution_id=created["execution_id"],
                expected_state="pending",
                expected_version=0,
                new_state=new_state,
                actor=f"worker-{new_state}",
                reason=f"worker_selected_{new_state}",
            )
            return ("committed", value["state"])
        except ExecutionStateConflict:
            return ("conflict", new_state)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(worker, ("running", "failed")))

    assert sorted(result[0] for result in results) == ["committed", "conflict"]
    snapshot = execution_snapshot(created["execution_id"])
    assert snapshot is not None
    assert snapshot["state"] in {"running", "failed"}
    assert snapshot["state_version"] == 1
    assert snapshot["event_count"] == 2
    assert snapshot["ledger_consistent"] is True


@pytest.mark.parametrize("dialect", [sqlite.dialect(), postgresql.dialect()])
def test_v35_1_compare_and_swap_sql_contract_is_cross_dialect(dialect):
    statement = _transition_statement(
        execution_id="execution-1",
        expected_state="pending",
        expected_version=0,
        new_state="running",
        actor="operator",
        reason="delegate_invoked",
    )
    compiled = str(statement.compile(dialect=dialect))

    assert "governance_executions" in compiled
    assert "current_state" in compiled
    assert "state_version" in compiled
    assert "execution_id" in compiled


@pytest.mark.skipif(
    not os.getenv("SOCMINT_TEST_POSTGRES_URL"),
    reason="SOCMINT_TEST_POSTGRES_URL is not configured",
)
def test_v35_1_postgres_runtime_transition_contract():
    database.configure_database(os.environ["SOCMINT_TEST_POSTGRES_URL"], create_schema=True)
    reset_execution_ledger_for_tests()
    created = _create("c" * 64)
    running = transition_execution(
        execution_id=created["execution_id"],
        expected_state="pending",
        expected_version=0,
        new_state="running",
        actor="postgres-worker",
        reason="postgres_compare_and_swap",
    )
    assert running["state"] == "running"
    assert running["state_version"] == 1
    assert running["ledger_consistent"] is True
