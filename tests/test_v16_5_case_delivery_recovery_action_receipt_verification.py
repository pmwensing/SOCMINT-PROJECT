from __future__ import annotations

from pathlib import Path

from src.socmint.case_delivery_recovery_action_receipt_v16_4 import build_case_delivery_recovery_action_receipt
from src.socmint.case_delivery_recovery_action_receipt_verification_v16_5 import (
    CASE_DELIVERY_RECOVERY_ACTION_RECEIPT_VERIFICATION_SCHEMA,
)
from src.socmint.case_delivery_recovery_action_receipt_verification_v16_5 import (
    verify_case_delivery_recovery_action_receipt,
)
from src.socmint.case_delivery_recovery_v16_3 import build_case_delivery_recovery
from src.socmint.case_delivery_workspace_routes_v15 import register_case_delivery_workspace_routes_v15
from src.socmint.dashboard import create_app
from tests.test_v15_case_delivery_workspace import ready_payload


def _issued_receipt(detail: str = "Recipient did not acknowledge.", *, status: str = "completed"):
    recovery = build_case_delivery_recovery(
        "case-v16-5-verify",
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
                }
            ],
        ),
    )
    queue_item = recovery["operator_recovery_queue"][0]
    receipt_result = build_case_delivery_recovery_action_receipt(
        "case-v16-5-verify",
        {
            "recovery": recovery,
            "operator": "delivery-lead",
            "actions": [
                {
                    "recovery_id": queue_item["recovery_id"],
                    "status": status,
                    "operator": "delivery-lead",
                    "detail": "Operator action completed.",
                }
            ],
        },
    )
    return recovery, receipt_result["receipt"]


def test_case_delivery_recovery_action_receipt_verification_passes_valid_receipt():
    recovery, receipt = _issued_receipt()

    result = verify_case_delivery_recovery_action_receipt(receipt, recovery)

    assert result["schema"] == CASE_DELIVERY_RECOVERY_ACTION_RECEIPT_VERIFICATION_SCHEMA
    assert result["status"] == "verified"
    assert result["verified"] is True
    assert result["receipt_id"] == receipt["receipt_id"]
    assert result["queue_id"] == recovery["queue_id"]
    assert result["blocker_count"] == 0


def test_case_delivery_recovery_action_receipt_verification_blocks_tampered_receipt_id():
    recovery, receipt = _issued_receipt()
    tampered = {**receipt, "receipt_id": "tampered"}

    result = verify_case_delivery_recovery_action_receipt(tampered, recovery)

    assert result["status"] == "blocked"
    assert result["verified"] is False
    assert any(blocker["key"] == "receipt_id_mismatch" for blocker in result["blockers"])


def test_case_delivery_recovery_action_receipt_verification_blocks_queue_mismatch():
    recovery, receipt = _issued_receipt()
    tampered = {**receipt, "queue_id": "different-queue"}

    result = verify_case_delivery_recovery_action_receipt(tampered, recovery)

    assert result["status"] == "blocked"
    assert any(blocker["key"] == "queue_id_mismatch" for blocker in result["blockers"])
    assert any(blocker["key"] == "receipt_id_mismatch" for blocker in result["blockers"])


def test_case_delivery_recovery_action_receipt_verification_blocks_tampered_action_receipt_id():
    recovery, receipt = _issued_receipt()
    tampered_actions = [{**receipt["actions"][0], "action_receipt_id": "tampered-action"}]
    tampered = {**receipt, "actions": tampered_actions}

    result = verify_case_delivery_recovery_action_receipt(tampered, recovery)

    assert result["status"] == "blocked"
    assert any(blocker["key"] == "action_receipt_id_mismatch" for blocker in result["blockers"])
    assert any(blocker["key"] == "receipt_id_mismatch" for blocker in result["blockers"])


def test_case_delivery_recovery_action_receipt_verification_blocks_recovery_mismatch():
    recovery, receipt = _issued_receipt()
    tampered_actions = [{**receipt["actions"][0], "decision": "escalate"}]
    tampered = {**receipt, "actions": tampered_actions}

    result = verify_case_delivery_recovery_action_receipt(tampered, recovery)

    assert result["status"] == "blocked"
    assert any(blocker["key"] == "decision_mismatch" for blocker in result["blockers"])
    assert any(blocker["key"] == "action_receipt_id_mismatch" for blocker in result["blockers"])


def test_case_delivery_recovery_action_receipt_verification_blocks_when_recovery_blocked():
    recovery = build_case_delivery_recovery(
        "case-v16-5-blocked",
        ready_payload(
            operator="operator",
            issuer="release-lead",
            authorizer="delivery-lead",
            events=[{"type": "exception", "operator": "delivery-lead", "detail": "Channel outage."}],
        ),
    )

    result = verify_case_delivery_recovery_action_receipt({}, recovery)

    assert result["status"] == "blocked"
    assert any(blocker["key"] == "missing_receipt" for blocker in result["blockers"])
    assert any(blocker["key"] == "recovery_blocked" for blocker in result["blockers"])


def test_case_delivery_recovery_action_receipt_verification_route_requires_login(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_case_delivery_workspace_routes_v15(app)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["_csrf_token"] = "test-csrf"

    response = client.post(
        "/api/v1/case-delivery/case-1/recovery-action-receipt/verify",
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert response.status_code == 401


def test_case_delivery_recovery_action_receipt_verification_route_returns_verified(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_case_delivery_workspace_routes_v15(app)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user"] = "operator"
        sess["is_admin"] = False
        sess["_csrf_token"] = "test-csrf"

    recovery, receipt = _issued_receipt()
    response = client.post(
        "/api/v1/case-delivery/case-1/recovery-action-receipt/verify",
        json={"recovery": recovery, "receipt": receipt},
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "verified"
    assert payload["verified"] is True
    assert payload["receipt_id"] == receipt["receipt_id"]


def test_v16_5_release_note_and_changelog_are_present():
    note = Path("release/V16_5_DELIVERY_RECOVERY_ACTION_RECEIPT_VERIFICATION.md").read_text(encoding="utf-8")
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert "/api/v1/case-delivery/<case_id>/recovery-action-receipt/verify" in note
    assert "v16.5 Delivery Recovery Action Receipt Verification" in changelog
