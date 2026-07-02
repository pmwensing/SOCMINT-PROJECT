from __future__ import annotations

import os
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pytest

from src.socmint import database
from src.socmint.durable_execution_ledger_v35_1 import (
    GovernanceExecution,
    create_execution,
    transition_execution,
)
from src.socmint.execution_reconciliation_service_v35_4 import reconcile_execution
from src.socmint.governance_execution_result_model_v35_3 import (
    GovernanceExecutionResult,
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


def _setup(name: str) -> dict[str, Any]:
    service = "recall_retention_lifecycle_v32_6.record_retention_decision"
    digest_a = ("a" if name == "identical" else "d") * 64
    digest_b = ("b" if name == "identical" else "e") * 64
    digest_c = ("c" if name == "identical" else "f") * 64
    contract = {
        "status": "confirmation_required",
        "case_id": f"case-v35-4-pg-{name}",
        "action": "record_retention_decision",
        "delegate_service": service,
        "eligibility_resolution_sha256": digest_c,
        "targets": {},
        "inputs": {
            "disposition": "retain",
            "policy_id": f"policy-{name}",
            "reason": "postgres reconciliation test",
        },
        "impact_summary": "Confirm retention decision",
    }
    identity = confirmation_identity(contract)
    assert identity is not None
    contract.update(identity)
    issuance = record_issued_confirmation(contract, "admin")
    created = create_execution(
        confirmation_sha256=contract["confirmation_sha256"],
        actor="admin",
        case_id=contract["case_id"],
        governance_action=contract["action"],
        delegate_service=service,
    )
    running = transition_execution(
        execution_id=created["execution_id"],
        expected_state="pending",
        expected_version=created["state_version"],
        new_state="running",
        actor="admin",
        reason="authoritative_delegate_invocation_started",
        metadata={
            "confirmation_issue_audit_id": issuance["audit_record_id"],
            "contract_validation_sha256": digest_a,
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
            "result_reference_sha256": digest_b,
            "authoritative_record_ids": {"decision_id": f"decision-{name}"},
        },
    )
    return {
        "case_id": contract["case_id"],
        "execution_id": created["execution_id"],
        "expected_version": uncertain["state_version"],
        "result_reference_sha256": digest_b,
        "workspace_sha256": digest_c,
        "decision_id": f"decision-{name}",
    }


def _payload(setup: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "expected_state": "uncertain",
        "expected_version": setup["expected_version"],
        "authoritative_record_ids": {"decision_id": setup["decision_id"]},
        "result_reference_sha256": setup["result_reference_sha256"],
        "workspace_sha256": setup["workspace_sha256"],
        "reconciliation_reason": reason,
        "evidence_references": [
            {"reference_type": "audit", "reference_id": f"audit-{reason}"}
        ],
    }


def _race(setup, payloads):
    barrier = threading.Barrier(len(payloads))

    def invoke(payload):
        barrier.wait(timeout=10)
        try:
            return "ok", reconcile_execution(
                setup["execution_id"], payload, actor="admin"
            )
        except Exception as exc:
            return "error", exc

    with ThreadPoolExecutor(max_workers=len(payloads)) as executor:
        futures = [executor.submit(invoke, payload) for payload in payloads]
        return [future.result(timeout=30) for future in futures]


def _assert_one_result(setup):
    session = database.Session()
    try:
        execution = session.query(GovernanceExecution).filter_by(
            execution_id=setup["execution_id"]
        ).one()
        assert execution.current_state == "reconciled"
        assert execution.state_version == 3
        assert (
            session.query(GovernanceExecutionResult)
            .filter_by(execution_id=setup["execution_id"])
            .count()
            == 1
        )
    finally:
        session.close()


def test_postgres_identical_reconciliation_workers_replay_one_result():
    _configure()
    setup = _setup("identical")
    payload = _payload(setup, "verified-identical")

    outcomes = _race(setup, [payload, dict(payload)])

    assert [status for status, _ in outcomes] == ["ok", "ok"]
    reconciliations = [item["reconciliation"] for _, item in outcomes]
    assert sorted(item["created"] for item in reconciliations) == [False, True]
    assert sorted(item["replay_detected"] for item in reconciliations) == [False, True]
    _assert_one_result(setup)


def test_postgres_conflicting_reconciliation_workers_preserve_first():
    _configure()
    setup = _setup("conflicting")

    outcomes = _race(
        setup,
        [
            _payload(setup, "verified-a"),
            _payload(setup, "verified-b"),
        ],
    )

    successes = [item for status, item in outcomes if status == "ok"]
    failures = [item for status, item in outcomes if status == "error"]
    assert len(successes) == 1
    assert len(failures) == 1
    assert isinstance(failures[0], ExecutionResultConflict)
    _assert_one_result(setup)
