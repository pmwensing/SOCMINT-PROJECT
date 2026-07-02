import pytest

from src.socmint import database
from src.socmint.durable_execution_ledger_v35_1 import execution_snapshot
from src.socmint.governance_action_execution_v34_3_6 import (
    execute_confirmed_action,
    reset_confirmation_consumption_for_tests,
)
from src.socmint.governance_action_routes_v34_2_6 import DELEGATES
from src.socmint.governance_execution_hardening_v34_8 import (
    audit_delegate_signatures,
    claim_confirmation,
    confirmation_claimed,
    reset_execution_ledger_for_tests,
)


ACTION_PAYLOADS = {
    "create_audience_contract": {
        "targets": {},
        "inputs": {
            "audience_name": "Legal Review",
            "audience_type": "legal",
            "dissemination_purpose": "case review",
            "classification": "restricted",
            "recipients": [{"recipient_id": "recipient-1"}],
            "reason": "approved review workflow",
        },
    },
    "record_delivery_attempt": {
        "targets": {"dissemination_package_id": "package-1"},
        "inputs": {
            "recipient_id": "recipient-1",
            "delivery_channel": "secure_portal",
            "endpoint_reference": "reference-1",
            "attempt_result": "accepted",
            "transport_reference": "transport-1",
            "reason": "confirmed delivery attempt",
        },
    },
    "record_correction_intake": {
        "targets": {"recipient_feedback_id": "feedback-1"},
        "inputs": {
            "correction_action": "editorial_review",
            "reason": "recipient reported an error",
            "affected_section_ids": ["section-1"],
        },
    },
    "record_retention_decision": {
        "targets": {},
        "inputs": {
            "disposition": "retain",
            "policy_id": "policy-1",
            "reason": "retention policy applies",
        },
    },
}


def _contract(action, service, confirmation_id, confirmation_sha256, case_id="case-1"):
    payload = ACTION_PAYLOADS[action]
    return {
        "status": "confirmation_required",
        "case_id": case_id,
        "action": action,
        "delegate_service": service,
        "confirmation_id": confirmation_id,
        "confirmation_sha256": confirmation_sha256,
        "targets": dict(payload["targets"]),
        "inputs": dict(payload["inputs"]),
    }


def test_v34_8_actual_delegate_signatures_are_compatible():
    report = audit_delegate_signatures(DELEGATES)
    assert report["status"] == "passed", report["checks"]
    assert report["compatible_count"] == report["delegate_count"] == 8


def test_v34_8_confirmation_claim_survives_process_local_state(tmp_path):
    database.configure_database(f"sqlite:///{tmp_path / 'replay.db'}")
    reset_execution_ledger_for_tests()

    first = claim_confirmation(
        confirmation_sha256="digest-1",
        actor="admin",
        case_id="case-1",
        action="record_retention_decision",
    )
    assert first and first["audit_record_id"]
    assert confirmation_claimed("digest-1") is True

    duplicate = claim_confirmation(
        confirmation_sha256="digest-1",
        actor="other-worker",
        case_id="case-1",
        action="record_retention_decision",
    )
    assert duplicate is None


@pytest.mark.parametrize(
    ("action", "family", "service"),
    [
        (
            "create_audience_contract",
            "audience_package_authorization",
            "audience_recipient_contract_v32_1.record_audience_recipient_contract",
        ),
        (
            "record_delivery_attempt",
            "delivery_retry",
            "delivery_attempt_receipt_ledger_v32_4.record_delivery_attempt",
        ),
        (
            "record_correction_intake",
            "feedback_correction",
            "recipient_feedback_correction_intake_v32_5.record_correction_intake",
        ),
        (
            "record_retention_decision",
            "recall_retention",
            "recall_retention_lifecycle_v32_6.record_retention_decision",
        ),
    ],
)
def test_v34_8_operator_acceptance_across_action_families(
    monkeypatch, tmp_path, action, family, service
):
    database.configure_database(
        f"sqlite:///{tmp_path / f'{action}.db'}", create_schema=True
    )
    reset_confirmation_consumption_for_tests()
    calls = []
    monkeypatch.setattr(
        "src.socmint.governance_action_execution_v34_3_6.record_execution_result",
        lambda **kwargs: {"audit_record_id": 11},
    )
    monkeypatch.setattr(
        "src.socmint.governance_action_execution_v34_3_6.refreshed_workspace",
        lambda case_id: {"case_id": case_id, "workspace_sha256": "workspace-sha"},
    )
    contract = _contract(
        action,
        service,
        confirmation_id="confirm-1",
        confirmation_sha256=f"sha-{action}",
    )
    delegates = {
        service: lambda **kwargs: calls.append(kwargs)
        or {"audit_record_id": 55, "domain_record_id": "domain-1"}
    }

    cancelled = execute_confirmed_action(
        contract, "confirm-1", False, "admin", delegates
    )
    assert cancelled["execution_performed"] is False
    assert cancelled["confirmation_consumed"] is False
    assert calls == []

    result = execute_confirmed_action(
        contract, "confirm-1", True, "admin", delegates
    )
    assert result["status"] == "executed"
    assert result["action_family"] == family
    assert result["confirmation_claim_audit"]["audit_record_id"]
    assert result["execution_audit"]["audit_record_id"] == 11
    assert result["execution_state"] == "succeeded"
    assert result["state_version"] == 2
    assert result["execution_ledger_consistent"] is True
    assert result["authoritative_record_ids"] == {
        "audit_record_id": 55,
        "domain_record_id": "domain-1",
    }
    assert result["workspace_sha256"] == "workspace-sha"
    assert result["durable_replay_protection"] is True
    assert result["contract_validation"]["valid"] is True
    assert result["automatic_retry"] is False
    assert len(calls) == 1


def test_v35_1_delegate_exception_becomes_uncertain_without_retry(tmp_path):
    database.configure_database(
        f"sqlite:///{tmp_path / 'uncertain.db'}", create_schema=True
    )
    reset_confirmation_consumption_for_tests()
    service = "delivery_attempt_receipt_ledger_v32_4.record_delivery_attempt"
    contract = _contract(
        "record_delivery_attempt",
        service,
        confirmation_id="confirm-uncertain",
        confirmation_sha256="uncertain-confirmation",
        case_id="case-uncertain",
    )
    calls = []

    def delegate(**kwargs):
        calls.append(kwargs)
        raise RuntimeError("connection lost after invocation")

    result = execute_confirmed_action(
        contract,
        "confirm-uncertain",
        True,
        "admin",
        {service: delegate},
    )

    assert result["status"] == "uncertain"
    assert result["execution_state"] == "uncertain"
    assert result["state_version"] == 2
    assert result["external_effect_unknown"] is True
    assert result["contract_validation"]["valid"] is True
    assert result["automatic_retry"] is False
    assert len(calls) == 1
    snapshot = execution_snapshot(result["execution_id"])
    assert snapshot is not None
    assert snapshot["state"] == "uncertain"
    assert snapshot["ledger_consistent"] is True

    duplicate = execute_confirmed_action(
        contract,
        "confirm-uncertain",
        True,
        "admin",
        {service: delegate},
    )
    assert duplicate["status"] == "duplicate_rejected"
    assert len(calls) == 1


def test_v35_1_pre_invocation_failure_is_failed(monkeypatch, tmp_path):
    database.configure_database(
        f"sqlite:///{tmp_path / 'failed.db'}", create_schema=True
    )
    reset_confirmation_consumption_for_tests()
    service = "delivery_attempt_receipt_ledger_v32_4.record_delivery_attempt"
    contract = _contract(
        "record_delivery_attempt",
        service,
        confirmation_id="confirm-failed",
        confirmation_sha256="failed-confirmation",
        case_id="case-failed",
    )
    calls = []
    monkeypatch.setattr(
        "src.socmint.governance_action_execution_v34_3_6._delegate_kwargs",
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("invalid input")),
    )

    result = execute_confirmed_action(
        contract,
        "confirm-failed",
        True,
        "admin",
        {service: lambda **kwargs: calls.append(kwargs)},
    )

    assert result["status"] == "failed"
    assert result["execution_state"] == "failed"
    assert result["state_version"] == 1
    assert result["execution_performed"] is False
    assert result["execution_created"] is True
    assert result["automatic_retry"] is False
    assert calls == []
