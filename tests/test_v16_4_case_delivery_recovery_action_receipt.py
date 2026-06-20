from __future__ import annotations

from pathlib import Path

import pytest

from src.socmint.case_delivery_recovery_action_receipt_v16_4 import (
    CASE_DELIVERY_RECOVERY_ACTION_RECEIPT_SCHEMA,
)
from src.socmint.case_delivery_recovery_action_receipt_v16_4 import (
    build_case_delivery_recovery_action_receipt,
)
from src.socmint.case_delivery_recovery_v16_3 import build_case_delivery_recovery
from src.socmint.case_delivery_workspace_routes_v15 import (
    register_case_delivery_workspace_routes_v15,
)
from src.socmint.dashboard import create_app
from tests.test_v15_case_delivery_workspace import ready_payload


def _recovery_for_attempt(detail: str, *, retryable: bool = True):
    return build_case_delivery_recovery(
        "case-v16-4-receipt",
        ready_payload(
            operator="operator",
            issuer="release-lead",
            authorizer="delivery-lead",
            attempts=[
                {
                    "channel": "secure_portal",
                    "status": "failed",
                    "operator": "delivery-lead",
                    "detail": detail,
                    "retryable": retryable,
                }
            ],
        ),
    )


def test_case_delivery_recovery_action_receipt_records_completed_retry():
    recovery = _recovery_for_attempt("Recipient did not acknowledge.")
    queue_item = recovery["operator_recovery_queue"][0]
    result = build_case_delivery_recovery_action_receipt(
        "case-v16-4-receipt",
        {
            "recovery": recovery,
            "operator": "delivery-lead",
            "actions": [
                {
                    "recovery_id": queue_item["recovery_id"],
                    "status": "completed",
                    "operator": "delivery-lead",
                    "detail": "Recipient confirmed and retry completed.",
                }
            ],
        },
    )

    assert result["status"] == "issued"
    assert result["receipt_id"]
    assert result["receipt"]["schema"] == CASE_DELIVERY_RECOVERY_ACTION_RECEIPT_SCHEMA
    assert result["receipt"]["status"] == "completed"
    assert result["receipt"]["completed_count"] == 1
    assert result["receipt"]["pending_count"] == 0
    assert result["receipt"]["actions"][0]["decision"] == "retry"
    assert result["receipt"]["actions"][0]["action_status"] == "completed"
    assert result["receipt"]["actions"][0]["completed"] is True
    assert result["next_action"] == "continue_delivery"


@pytest.mark.parametrize(
    "detail, retryable, expected_decision, action_status, expected_receipt_status",
    [
        ("Channel outage.", True, "remediate", "resolved", "completed"),
        ("Recipient rejected delivery.", True, "escalate", "acknowledged", "completed"),
        ("Timeout waiting for recipient.", False, "hold", "deferred", "pending"),
    ],
)
def test_case_delivery_recovery_action_receipt_records_recovery_decisions(
    detail,
    retryable,
    expected_decision,
    action_status,
    expected_receipt_status,
):
    recovery = _recovery_for_attempt(detail, retryable=retryable)
    queue_item = recovery["operator_recovery_queue"][0]

    result = build_case_delivery_recovery_action_receipt(
        "case-v16-4-decision",
        {
            "recovery": recovery,
            "operator": "delivery-lead",
            "actions": [
                {
                    "recovery_id": queue_item["recovery_id"],
                    "status": action_status,
                    "operator": "delivery-lead",
                    "detail": "Operator action recorded.",
                }
            ],
        },
    )

    assert result["status"] == "issued"
    assert result["receipt"]["actions"][0]["decision"] == expected_decision
    assert result["receipt"]["actions"][0]["action_status"] == action_status
    assert result["receipt"]["status"] == expected_receipt_status


def test_case_delivery_recovery_action_receipt_id_is_deterministic_and_payload_sensitive():
    recovery = _recovery_for_attempt("Recipient did not acknowledge.")
    queue_item = recovery["operator_recovery_queue"][0]
    payload = {
        "recovery": recovery,
        "operator": "delivery-lead",
        "actions": [
            {
                "recovery_id": queue_item["recovery_id"],
                "status": "completed",
                "operator": "delivery-lead",
                "detail": "Retry completed.",
            }
        ],
    }

    first = build_case_delivery_recovery_action_receipt("case-v16-4-stable", payload)
    second = build_case_delivery_recovery_action_receipt("case-v16-4-stable", payload)
    changed = build_case_delivery_recovery_action_receipt(
        "case-v16-4-stable",
        {
            **payload,
            "actions": [
                {
                    **payload["actions"][0],
                    "status": "pending",
                }
            ],
        },
    )

    assert first["receipt_id"] == second["receipt_id"]
    assert first["receipt_id"] != changed["receipt_id"]


def test_case_delivery_recovery_action_receipt_blocks_when_recovery_is_blocked():
    result = build_case_delivery_recovery_action_receipt(
        "case-v16-4-blocked",
        ready_payload(
            operator="operator",
            issuer="release-lead",
            authorizer="delivery-lead",
            events=[
                {
                    "type": "exception",
                    "operator": "delivery-lead",
                    "detail": "Channel outage.",
                }
            ],
            actions=[{"status": "completed", "operator": "delivery-lead"}],
        ),
    )

    assert result["status"] == "blocked"
    assert result["receipt"] is None
    assert result["receipt_id"] is None
    assert any(blocker["key"] == "recovery_blocked" for blocker in result["blockers"])
    assert result["next_action"] == "complete_recovery_actions"


def test_case_delivery_recovery_action_receipt_route_requires_login(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_case_delivery_workspace_routes_v15(app)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["_csrf_token"] = "test-csrf"

    response = client.post(
        "/api/v1/case-delivery/case-1/recovery-action-receipt",
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert response.status_code == 401


def test_case_delivery_recovery_action_receipt_route_returns_issued_receipt(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_case_delivery_workspace_routes_v15(app)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user"] = "operator"
        sess["is_admin"] = False
        sess["_csrf_token"] = "test-csrf"

    recovery = _recovery_for_attempt("Recipient did not acknowledge.")
    queue_item = recovery["operator_recovery_queue"][0]
    response = client.post(
        "/api/v1/case-delivery/case-1/recovery-action-receipt",
        json={
            "recovery": recovery,
            "operator": "delivery-lead",
            "actions": [
                {
                    "recovery_id": queue_item["recovery_id"],
                    "status": "confirmed",
                    "operator": "delivery-lead",
                    "detail": "Retry confirmed.",
                }
            ],
        },
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "issued"
    assert payload["receipt_id"]
    assert payload["receipt"]["status"] == "completed"


def test_v16_4_release_note_and_changelog_are_present():
    note = Path("release/V16_4_DELIVERY_RECOVERY_ACTION_RECEIPT.md").read_text(
        encoding="utf-8"
    )
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert "/api/v1/case-delivery/<case_id>/recovery-action-receipt" in note
    assert "v16.4 Delivery Recovery Action Receipt" in changelog
