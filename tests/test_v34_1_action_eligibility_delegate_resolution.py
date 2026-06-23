from copy import deepcopy

from src.socmint.action_eligibility_delegate_resolution_v34_1 import (
    build_action_eligibility_delegate_resolution,
)


def _queue_item(**overrides):
    item = {
        "case_id": "case-1",
        "action_queue_item_id": "queue-1",
        "action": "record_delivery_attempt",
        "stage": "delivery",
        "priority": 40,
        "severity": "high",
        "delegate_service": (
            "delivery_attempt_receipt_ledger_v32_4.record_delivery_attempt"
        ),
        "targets": {
            "dissemination_package_id": "package-1",
            "authorization_decision_id": "authorization-1",
        },
        "confirmation_required": True,
        "automatic_execution_allowed": False,
    }
    item.update(overrides)
    return item


def test_v34_1_resolves_eligible_action_without_execution(monkeypatch):
    queue = {
        "status": "attention_required",
        "case_id": "case-1",
        "queue_summary_sha256": "queue-sha",
        "action_queue": [_queue_item()],
        "blockers": [],
    }
    original = deepcopy(queue)
    monkeypatch.setattr(
        "src.socmint.action_eligibility_delegate_resolution_v34_1."
        "build_case_action_queue",
        lambda case_id: queue,
    )

    payload = build_action_eligibility_delegate_resolution("case-1")

    assert payload["schema"] == (
        "socmint.action_eligibility_delegate_resolution.v34_1"
    )
    assert payload["version"] == "v34.1.0"
    assert payload["status"] == "ready_for_confirmation"
    assert payload["eligible_count"] == 1
    assert payload["blocked_count"] == 0
    resolution = payload["resolutions"][0]
    assert resolution["eligible"] is True
    assert resolution["delegate_module"] == (
        "delivery_attempt_receipt_ledger_v32_4"
    )
    assert resolution["delegate_function"] == "record_delivery_attempt"
    assert resolution["execution_performed"] is False
    assert payload["read_only"] is True
    assert payload["source_records_mutated"] is False
    assert queue == original


def test_v34_1_blocks_delegate_mismatch_and_missing_targets(monkeypatch):
    monkeypatch.setattr(
        "src.socmint.action_eligibility_delegate_resolution_v34_1."
        "build_case_action_queue",
        lambda case_id: {
            "status": "attention_required",
            "case_id": case_id,
            "queue_summary_sha256": "queue-sha",
            "action_queue": [
                _queue_item(
                    delegate_service="unexpected.service",
                    targets={"dissemination_package_id": "package-1"},
                )
            ],
            "blockers": [],
        },
    )

    payload = build_action_eligibility_delegate_resolution("case-1")

    assert payload["status"] == "review_required"
    assert payload["eligible_count"] == 0
    assert payload["blocked_count"] == 1
    resolution = payload["resolutions"][0]
    assert resolution["eligible"] is False
    assert {item["key"] for item in resolution["eligibility_blockers"]} == {
        "delegate_service_mismatch",
        "required_target_missing",
    }
    assert resolution["missing_targets"] == ["authorization_decision_id"]


def test_v34_1_preserves_blocked_queue_state(monkeypatch):
    monkeypatch.setattr(
        "src.socmint.action_eligibility_delegate_resolution_v34_1."
        "build_case_action_queue",
        lambda case_id: {
            "status": "blocked",
            "case_id": case_id,
            "blockers": [{"key": "case_not_found"}],
        },
    )

    payload = build_action_eligibility_delegate_resolution("missing")

    assert payload["status"] == "blocked"
    assert payload["resolutions"] == []
    assert payload["execution_performed"] is False
    assert payload["source_records_mutated"] is False


def test_v34_1_is_deterministic(monkeypatch):
    monkeypatch.setattr(
        "src.socmint.action_eligibility_delegate_resolution_v34_1."
        "build_case_action_queue",
        lambda case_id: {
            "status": "attention_required",
            "case_id": case_id,
            "queue_summary_sha256": "queue-sha",
            "action_queue": [_queue_item()],
            "blockers": [],
        },
    )

    first = build_action_eligibility_delegate_resolution("case-1")
    second = build_action_eligibility_delegate_resolution("case-1")

    assert first["resolution_summary_sha256"] == second[
        "resolution_summary_sha256"
    ]
    assert first["resolutions"][0]["eligibility_resolution_sha256"] == second[
        "resolutions"
    ][0]["eligibility_resolution_sha256"]
