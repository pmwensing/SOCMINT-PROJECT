from src.socmint import database
from src.socmint.durable_execution_ledger_v35_1 import (
    LEDGER_ACTION,
    GovernanceExecution,
)
from src.socmint.governance_action_execution_v34_3_6 import (
    execute_confirmed_action,
    reset_confirmation_consumption_for_tests,
)


def _configure(tmp_path):
    database.configure_database(
        f"sqlite:///{tmp_path / 'execution-gate.db'}",
        create_schema=True,
    )
    reset_confirmation_consumption_for_tests()


def _retention_contract():
    return {
        "status": "confirmation_required",
        "case_id": "case-1",
        "action": "record_retention_decision",
        "delegate_service": (
            "recall_retention_lifecycle_v32_6.record_retention_decision"
        ),
        "confirmation_id": "confirm-1",
        "confirmation_sha256": "confirmation-sha-1",
        "targets": {},
        "inputs": {
            "disposition": "retain",
            "reason": "retention policy applies",
        },
    }


def _ledger_counts():
    session = database.Session()
    try:
        execution_count = session.query(GovernanceExecution).count()
        event_count = (
            session.query(database.AuditLog)
            .filter_by(action=LEDGER_ACTION)
            .count()
        )
        return execution_count, event_count
    finally:
        session.close()


def test_invalid_contract_does_not_create_or_consume_execution(tmp_path):
    _configure(tmp_path)
    contract = _retention_contract()
    calls = []
    service = contract["delegate_service"]

    result = execute_confirmed_action(
        contract,
        contract["confirmation_id"],
        True,
        "admin",
        {service: lambda **kwargs: calls.append(kwargs)},
    )

    assert result["status"] == "blocked"
    assert result["reason"] == "action_contract_invalid"
    assert result["confirmation_accepted"] is True
    assert result["confirmation_consumed"] is False
    assert result["execution_attempted"] is False
    assert result["execution_created"] is False
    assert result["contract_validation"]["valid"] is False
    assert result["contract_validation"]["errors"] == [
        {"key": "required_field_missing", "field": "policy_id"}
    ]
    assert calls == []
    assert _ledger_counts() == (0, 0)


def test_rejected_contract_can_be_resubmitted_without_duplicate_state(tmp_path):
    _configure(tmp_path)
    contract = _retention_contract()
    service = contract["delegate_service"]

    first = execute_confirmed_action(
        contract,
        contract["confirmation_id"],
        True,
        "admin",
        {service: lambda **kwargs: kwargs},
    )
    second = execute_confirmed_action(
        contract,
        contract["confirmation_id"],
        True,
        "admin",
        {service: lambda **kwargs: kwargs},
    )

    assert first["reason"] == second["reason"] == "action_contract_invalid"
    assert first["confirmation_consumed"] is False
    assert second["confirmation_consumed"] is False
    assert _ledger_counts() == (0, 0)
