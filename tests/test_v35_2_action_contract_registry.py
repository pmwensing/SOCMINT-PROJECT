from copy import deepcopy

import pytest

from src.socmint.action_contract_registry_v35_2 import (
    ACTION_CONTRACT_REGISTRY,
    SYSTEM_FIELDS,
    contract_for_action,
    registry_manifest,
)
from src.socmint.action_contract_validation_v35_2 import (
    audit_registry_against_services,
    validate_action_payload,
)
from src.socmint.action_eligibility_delegate_resolution_v34_1 import (
    DELEGATE_REGISTRY,
)
from src.socmint.governance_action_routes_v34_2_6 import DELEGATES


VALID_PAYLOADS = {
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
    "assemble_dissemination_package": {
        "targets": {"audience_contract_id": "audience-1"},
        "inputs": {
            "published_revision_id": "revision-1",
            "package_label": "Review package",
            "reason": "prepare approved package",
        },
    },
    "record_authorization_policy_decision": {
        "targets": {"dissemination_package_id": "package-1"},
        "inputs": {"decision": "approve", "reason": "policy checks passed"},
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
    "record_delivery_receipt": {
        "targets": {"delivery_attempt_id": "attempt-1"},
        "inputs": {
            "delivery_result": "delivered",
            "provider_message_id": "provider-1",
            "transport_status": "completed",
            "delivered_at": "2026-07-01T12:00:00Z",
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
    "record_recall_decision": {
        "targets": {"correction_intake_id": "correction-1"},
        "inputs": {"decision": "initiate", "reason": "recall review accepted"},
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


def test_v35_2_registry_covers_exact_delegate_action_set():
    assert set(ACTION_CONTRACT_REGISTRY) == set(DELEGATE_REGISTRY)
    manifest = registry_manifest()
    assert manifest["action_count"] == 8
    assert len(manifest["registry_sha256"]) == 64
    assert manifest == registry_manifest()


def test_v35_2_registry_matches_actual_service_signatures():
    report = audit_registry_against_services(DELEGATES)
    assert report["status"] == "passed", report["checks"]
    assert report["compatible_count"] == report["action_count"] == 8
    assert len(report["audit_sha256"]) == 64


@pytest.mark.parametrize("action", sorted(VALID_PAYLOADS))
def test_v35_2_accepts_valid_payload_for_every_action(action):
    payload = VALID_PAYLOADS[action]
    before = deepcopy(payload)

    result = validate_action_payload(action, **payload)

    assert result["valid"] is True, result["errors"]
    assert result["errors"] == []
    assert result["normalized_fields"]
    assert payload == before
    assert len(result["validation_sha256"]) == 64


def test_v35_2_rejects_missing_required_field():
    result = validate_action_payload(
        "record_retention_decision",
        inputs={"disposition": "retain", "reason": "policy applies"},
    )
    assert result["valid"] is False
    assert {error["field"] for error in result["errors"]} == {"policy_id"}


@pytest.mark.parametrize("field", sorted(SYSTEM_FIELDS))
def test_v35_2_rejects_operator_supplied_system_fields(field):
    payload = deepcopy(VALID_PAYLOADS["record_retention_decision"])
    payload["inputs"][field] = "operator-value"

    result = validate_action_payload("record_retention_decision", **payload)

    assert result["valid"] is False
    assert {
        (error["key"], error["field"]) for error in result["errors"]
    } >= {("system_field_not_operator_supplied", field)}


def test_v35_2_rejects_unknown_and_duplicate_fields():
    result = validate_action_payload(
        "record_authorization_policy_decision",
        targets={"dissemination_package_id": "package-1", "decision": "approve"},
        inputs={
            "decision": "approve",
            "reason": "policy passed",
            "unexpected": "value",
        },
    )
    assert result["valid"] is False
    assert ("field_supplied_twice", "decision") in {
        (error["key"], error["field"]) for error in result["errors"]
    }
    assert ("unknown_field", "unexpected") in {
        (error["key"], error["field"]) for error in result["errors"]
    }


def test_v35_2_rejects_invalid_type_and_enum_value():
    result = validate_action_payload(
        "create_audience_contract",
        inputs={
            "audience_name": "Legal Review",
            "audience_type": "not-a-type",
            "dissemination_purpose": "review",
            "classification": "restricted",
            "recipients": "recipient-1",
            "reason": "review",
        },
    )
    assert result["valid"] is False
    pairs = {(error["key"], error["field"]) for error in result["errors"]}
    assert ("invalid_field_value", "audience_type") in pairs
    assert ("invalid_field_type", "recipients") in pairs


@pytest.mark.parametrize(
    ("action", "inputs", "required_field"),
    [
        (
            "record_delivery_attempt",
            {
                "recipient_id": "recipient-1",
                "delivery_channel": "portal",
                "endpoint_reference": "reference-1",
                "attempt_result": "failed",
                "transport_reference": "transport-1",
                "reason": "delivery failed",
            },
            "failure_code",
        ),
        (
            "record_delivery_receipt",
            {
                "delivery_result": "delivered",
                "provider_message_id": "provider-1",
                "transport_status": "completed",
            },
            "delivered_at",
        ),
        (
            "record_retention_decision",
            {
                "disposition": "expiry_review",
                "policy_id": "policy-1",
                "reason": "scheduled review",
            },
            "review_at",
        ),
    ],
)
def test_v35_2_enforces_conditional_requirements(action, inputs, required_field):
    target_fields = {
        "record_delivery_attempt": {"dissemination_package_id": "package-1"},
        "record_delivery_receipt": {"delivery_attempt_id": "attempt-1"},
        "record_retention_decision": {},
    }
    result = validate_action_payload(
        action,
        targets=target_fields[action],
        inputs=inputs,
    )
    assert result["valid"] is False
    assert ("conditional_field_required", required_field) in {
        (error["key"], error["field"]) for error in result["errors"]
    }


def test_v35_2_contract_copies_are_isolated_from_registry():
    first = contract_for_action("record_retention_decision")
    second = contract_for_action("record_retention_decision")
    assert first is not None and second is not None
    first["fields"].clear()
    assert second["fields"]
    assert ACTION_CONTRACT_REGISTRY["record_retention_decision"]["fields"]
