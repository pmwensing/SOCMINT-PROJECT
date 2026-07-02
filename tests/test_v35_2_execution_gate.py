import pytest

from src.socmint import database
from src.socmint.action_contract_validation_v35_2 import validate_action_payload
from src.socmint.durable_execution_ledger_v35_1 import (
    LEDGER_ACTION,
    GovernanceExecution,
)
from src.socmint.governance_action_execution_v34_3_6 import (
    execute_confirmed_action,
    reset_confirmation_consumption_for_tests,
)
from src.socmint.human_confirmation_framework_v34_2 import (
    confirmation_identity,
    record_issued_confirmation,
)


def _configure(tmp_path):
    database.configure_database(
        f"sqlite:///{tmp_path / 'execution-gate.db'}",
        create_schema=True,
    )
    reset_confirmation_consumption_for_tests()


def _retention_contract(*, valid=False, extra_inputs=None):
    service = "recall_retention_lifecycle_v32_6.record_retention_decision"
    inputs = {
        "disposition": "retain",
        "reason": "retention policy applies",
    }
    if valid:
        inputs["policy_id"] = "policy-1"
    inputs.update(extra_inputs or {})
    contract = {
        "status": "confirmation_required",
        "case_id": "case-1",
        "action": "record_retention_decision",
        "delegate_service": service,
        "eligibility_resolution_sha256": "eligibility-retention-1",
        "targets": {},
        "inputs": inputs,
        "impact_summary": (
            "Confirm record_retention_decision for case case-1 using "
            f"{service}"
        ),
    }
    identity = confirmation_identity(contract)
    assert identity is not None
    contract["confirmation_id"] = identity["confirmation_id"]
    contract["confirmation_sha256"] = identity["confirmation_sha256"]
    return contract


def _issue(contract):
    issuance = record_issued_confirmation(contract, "admin")
    assert issuance["issued"] is True
    return issuance


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
    _issue(contract)
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
    _issue(contract)
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


def test_operator_cannot_supply_system_controlled_reviewer(tmp_path):
    _configure(tmp_path)
    contract = _retention_contract(
        valid=True,
        extra_inputs={"reviewer": "supplied-reviewer"},
    )
    _issue(contract)
    service = contract["delegate_service"]

    result = execute_confirmed_action(
        contract,
        contract["confirmation_id"],
        True,
        "admin",
        {service: lambda **kwargs: kwargs},
    )

    assert result["reason"] == "action_contract_invalid"
    errors = {
        (item["key"], item["field"])
        for item in result["contract_validation"]["errors"]
    }
    assert ("system_field_not_operator_supplied", "reviewer") in errors
    assert "supplied-reviewer" not in repr(result)
    assert _ledger_counts() == (0, 0)


def test_mutated_issued_contract_is_rejected_before_execution(tmp_path):
    _configure(tmp_path)
    contract = _retention_contract(valid=True)
    _issue(contract)
    original_confirmation_id = contract["confirmation_id"]
    contract["inputs"]["reason"] = "different valid reason"
    service = contract["delegate_service"]
    calls = []

    result = execute_confirmed_action(
        contract,
        original_confirmation_id,
        True,
        "admin",
        {service: lambda **kwargs: calls.append(kwargs)},
    )

    assert result["reason"] == "confirmation_binding_invalid"
    assert result["confirmation_consumed"] is False
    assert result["execution_created"] is False
    assert calls == []
    assert _ledger_counts() == (0, 0)


def test_self_consistent_but_unissued_contract_is_rejected(tmp_path):
    _configure(tmp_path)
    contract = _retention_contract(valid=True)
    service = contract["delegate_service"]
    calls = []

    result = execute_confirmed_action(
        contract,
        contract["confirmation_id"],
        True,
        "admin",
        {service: lambda **kwargs: calls.append(kwargs)},
    )

    assert result["reason"] == "confirmation_not_issued"
    assert result["confirmation_consumed"] is False
    assert result["execution_created"] is False
    assert calls == []
    assert _ledger_counts() == (0, 0)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("targets", "not-a-mapping"),
        ("targets", ["bad"]),
        ("targets", 7),
        ("targets", True),
        ("inputs", "not-a-mapping"),
        ("inputs", ["bad"]),
        ("inputs", 7),
        ("inputs", True),
    ],
)
def test_malformed_payload_containers_are_structured_rejections(
    tmp_path,
    field,
    value,
):
    _configure(tmp_path)
    contract = _retention_contract(valid=True)
    contract[field] = value
    service = contract["delegate_service"]

    result = execute_confirmed_action(
        contract,
        contract["confirmation_id"],
        True,
        "admin",
        {service: lambda **kwargs: kwargs},
    )

    assert result["reason"] == "action_contract_invalid"
    assert result["execution_created"] is False
    assert result["confirmation_consumed"] is False
    assert (
        "invalid_container_type",
        field,
    ) in {
        (error["key"], error["field"])
        for error in result["contract_validation"]["errors"]
    }
    assert _ledger_counts() == (0, 0)


def test_validator_rejects_non_mapping_containers_without_raising():
    result = validate_action_payload(
        "record_retention_decision",
        targets="bad-targets",
        inputs=3,
    )
    assert result["valid"] is False
    errors = {(item["key"], item["field"]) for item in result["errors"]}
    assert ("invalid_container_type", "targets") in errors
    assert ("invalid_container_type", "inputs") in errors
