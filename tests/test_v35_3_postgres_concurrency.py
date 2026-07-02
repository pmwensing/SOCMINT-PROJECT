from __future__ import annotations

import os
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pytest

from src.socmint import database
from src.socmint.durable_execution_ledger_v35_1 import (
    LEDGER_ACTION,
    GovernanceExecution,
    create_execution,
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
)
from src.socmint.human_confirmation_framework_v34_2 import (
    confirmation_identity,
    record_issued_confirmation,
)

POSTGRES_URL = os.getenv("SOCMINT_POSTGRES_TEST_URL")
pytestmark = pytest.mark.skipif(
    not POSTGRES_URL,
    reason="SOCMINT_POSTGRES_TEST_URL is required",
)


def _configure() -> None:
    database.configure_database(POSTGRES_URL, create_schema=False)


def _running_execution(name: str) -> dict[str, Any]:
    service = "recall_retention_lifecycle_v32_6.record_retention_decision"
    contract = {
        "status": "confirmation_required",
        "case_id": f"case-pg-{name}",
        "action": "record_retention_decision",
        "delegate_service": service,
        "eligibility_resolution_sha256": f"eligibility-pg-{name}",
        "targets": {},
        "inputs": {
            "disposition": "retain",
            "policy_id": f"policy-{name}",
            "reason": "postgres concurrency verification",
        },
        "impact_summary": (
            f"Confirm record_retention_decision for case case-pg-{name} using "
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
    validation_sha = f"validation-pg-{name}"
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
        "case_id": contract["case_id"],
        "execution_id": created["execution_id"],
        "expected_version": running["state_version"],
        "confirmation_issue_audit_id": issuance["audit_record_id"],
        "contract_validation_sha256": validation_sha,
    }


def _completion_args(
    setup: dict[str, Any],
    *,
    record_id: str,
) -> dict[str, Any]:
    return {
        "execution_id": setup["execution_id"],
        "expected_version": setup["expected_version"],
        "actor": "admin",
        "confirmation_issue_audit_id": setup[
            "confirmation_issue_audit_id"
        ],
        "contract_validation_sha256": setup[
            "contract_validation_sha256"
        ],
        "authoritative_record_ids": {"domain_record_id": record_id},
        "result_reference_sha256": f"result-{record_id}",
        "workspace_sha256": f"workspace-{record_id}",
    }


def _race(*argument_sets: dict[str, Any]):
    barrier = threading.Barrier(len(argument_sets))

    def invoke(arguments):
        barrier.wait(timeout=10)
        try:
            return ("ok", complete_execution_result(**arguments))
        except Exception as exc:  # returned for deterministic race assertions
            return ("error", exc)

    with ThreadPoolExecutor(max_workers=len(argument_sets)) as executor:
        futures = [executor.submit(invoke, args) for args in argument_sets]
        return [future.result(timeout=30) for future in futures]


def _assert_single_durable_result(setup: dict[str, Any]) -> None:
    session = database.Session()
    try:
        execution = session.query(GovernanceExecution).filter_by(
            execution_id=setup["execution_id"]
        ).one()
        assert execution.current_state == "succeeded"
        assert execution.state_version == 2
        assert (
            session.query(GovernanceExecutionResult)
            .filter_by(execution_id=setup["execution_id"])
            .count()
            == 1
        )
        assert (
            session.query(database.AuditLog)
            .filter_by(action=RESULT_ACTION, target_value=setup["case_id"])
            .count()
            == 1
        )
        assert (
            session.query(database.AuditLog)
            .filter_by(action=LEDGER_ACTION, target_value=setup["execution_id"])
            .count()
            == 3
        )
    finally:
        session.close()


def test_postgres_identical_workers_create_one_result_and_one_replay():
    _configure()
    setup = _running_execution("identical")
    arguments = _completion_args(setup, record_id="record-identical")

    outcomes = _race(arguments, dict(arguments))

    assert [status for status, _ in outcomes] == ["ok", "ok"]
    payloads = [payload for _, payload in outcomes]
    assert sorted(payload["created"] for payload in payloads) == [False, True]
    assert sorted(payload["replay_detected"] for payload in payloads) == [False, True]
    assert len({payload["result"]["result_record_id"] for payload in payloads}) == 1
    _assert_single_durable_result(setup)


def test_postgres_conflicting_workers_preserve_first_result():
    _configure()
    setup = _running_execution("conflicting")
    first = _completion_args(setup, record_id="record-a")
    second = _completion_args(setup, record_id="record-b")

    outcomes = _race(first, second)

    successes = [payload for status, payload in outcomes if status == "ok"]
    failures = [payload for status, payload in outcomes if status == "error"]
    assert len(successes) == 1
    assert len(failures) == 1
    assert successes[0]["created"] is True
    assert isinstance(failures[0], ExecutionResultConflict)
    _assert_single_durable_result(setup)
