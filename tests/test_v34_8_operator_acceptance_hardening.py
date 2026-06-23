import pytest

from src.socmint import database
from src.socmint.governance_action_execution_v34_3_6 import (
    execute_confirmed_action,
)
from src.socmint.governance_action_routes_v34_2_6 import DELEGATES
from src.socmint.governance_execution_hardening_v34_8 import (
    audit_delegate_signatures,
    claim_confirmation,
    confirmation_claimed,
    reset_execution_ledger_for_tests,
)


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
    monkeypatch, action, family, service
):
    calls = []
    monkeypatch.setattr(
        "src.socmint.governance_action_execution_v34_3_6.claim_confirmation",
        lambda **kwargs: {"audit_record_id": 10},
    )
    monkeypatch.setattr(
        "src.socmint.governance_action_execution_v34_3_6.record_execution_result",
        lambda **kwargs: {"audit_record_id": 11},
    )
    monkeypatch.setattr(
        "src.socmint.governance_action_execution_v34_3_6.refreshed_workspace",
        lambda case_id: {"case_id": case_id, "workspace_sha256": "workspace-sha"},
    )
    contract = {
        "status": "confirmation_required",
        "case_id": "case-1",
        "action": action,
        "delegate_service": service,
        "confirmation_id": "confirm-1",
        "confirmation_sha256": f"sha-{action}",
        "targets": {},
        "inputs": {},
    }
    delegates = {
        service: lambda **kwargs: calls.append(kwargs)
        or {"audit_record_id": 55, "domain_record_id": "domain-1"}
    }

    cancelled = execute_confirmed_action(
        contract, "confirm-1", False, "admin", delegates
    )
    assert cancelled["execution_performed"] is False
    assert calls == []

    result = execute_confirmed_action(
        contract, "confirm-1", True, "admin", delegates
    )
    assert result["status"] == "executed"
    assert result["action_family"] == family
    assert result["confirmation_claim_audit"]["audit_record_id"] == 10
    assert result["execution_audit"]["audit_record_id"] == 11
    assert result["authoritative_record_ids"] == {
        "audit_record_id": 55,
        "domain_record_id": "domain-1",
    }
    assert result["workspace_sha256"] == "workspace-sha"
    assert result["durable_replay_protection"] is True
    assert len(calls) == 1
