from __future__ import annotations

from pathlib import Path

from src.socmint.case_delivery_recovery_action_receipt_v16_4 import build_case_delivery_recovery_action_receipt
from src.socmint.case_delivery_recovery_closure_record_v16_6 import CASE_DELIVERY_RECOVERY_CLOSURE_RECORD_SCHEMA
from src.socmint.case_delivery_recovery_closure_record_v16_6 import build_case_delivery_recovery_closure_record
from src.socmint.case_delivery_recovery_v16_3 import build_case_delivery_recovery
from src.socmint.case_delivery_workspace_routes_v15 import register_case_delivery_workspace_routes_v15
from src.socmint.dashboard import create_app
from tests.test_v15_case_delivery_workspace import ready_payload


def _closed_recovery_payload(status: str = "completed"):
    recovery = build_case_delivery_recovery(
        "case-v16-6-closure",
        ready_payload(
            operator="operator",
            issuer="release-lead",
            authorizer="delivery-lead",
            attempts=[
                {
                    "channel": "secure_portal",
                    "status": "failed",
                    "operator": "delivery-lead",
                    "detail": "Recipient did not acknowledge.",
                }
            ],
        ),
    )
    queue_item = recovery["operator_recovery_queue"][0]
    receipt_result = build_case_delivery_recovery_action_receipt(
        "case-v16-6-closure",
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


def test_case_delivery_recovery_closure_record_closes_verified_completed_receipt():
    recovery, receipt = _closed_recovery_payload()

    result = build_case_delivery_recovery_closure_record(recovery, receipt, closer="delivery-owner")

    assert result["status"] == "closed"
    assert result["closed"] is True
    assert result["closure"]["schema"] == CASE_DELIVERY_RECOVERY_CLOSURE_RECORD_SCHEMA
    assert result["closure"]["closed"] is True
    assert result["closure"]["closed_by"] == "delivery-owner"
    assert result["closure"]["receipt_id"] == receipt["receipt_id"]
    assert result["closure"]["queue_id"] == recovery["queue_id"]
    assert result["closure"]["closure_id"]
    assert result["receipt_verification"]["verified"] is True
    assert result["blocker_count"] == 0


def test_case_delivery_recovery_closure_record_id_is_deterministic_and_payload_sensitive():
    recovery, receipt = _closed_recovery_payload()

    first = build_case_delivery_recovery_closure_record(recovery, receipt, closer="delivery-owner")
    second = build_case_delivery_recovery_closure_record(recovery, receipt, closer="delivery-owner")
    changed = build_case_delivery_recovery_closure_record(recovery, receipt, closer="other-owner")

    assert first["closure"]["closure_id"] == second["closure"]["closure_id"]
    assert first["closure"]["closure_id"] != changed["closure"]["closure_id"]


def test_case_delivery_recovery_closure_record_blocks_pending_receipt():
    recovery, receipt = _closed_recovery_payload(status="pending")

    result = build_case_delivery_recovery_closure_record(recovery, receipt, closer="delivery-owner")

    assert result["status"] == "blocked"
    assert result["closed"] is False
    assert result["closure"] is None
    assert any(blocker["key"] == "receipt_not_complete" for blocker in result["blockers"])


def test_case_delivery_recovery_closure_record_blocks_tampered_receipt():
    recovery, receipt = _closed_recovery_payload()
    tampered = {**receipt, "receipt_id": "tampered"}

    result = build_case_delivery_recovery_closure_record(recovery, tampered, closer="delivery-owner")

    assert result["status"] == "blocked"
    assert result["closed"] is False
    assert result["closure"] is None
    assert any(blocker["key"] == "receipt_id_mismatch" for blocker in result["blockers"])
    assert any(blocker["key"] == "receipt_verification_blocked" for blocker in result["blockers"])


def test_case_delivery_recovery_closure_record_route_requires_login(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_case_delivery_workspace_routes_v15(app)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["_csrf_token"] = "test-csrf"

    response = client.post(
        "/api/v1/case-delivery/case-1/recovery-closure-record",
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert response.status_code == 401


def test_case_delivery_recovery_closure_record_route_returns_closed(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_case_delivery_workspace_routes_v15(app)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user"] = "operator"
        sess["is_admin"] = False
        sess["_csrf_token"] = "test-csrf"

    recovery, receipt = _closed_recovery_payload()
    response = client.post(
        "/api/v1/case-delivery/case-1/recovery-closure-record",
        json={"recovery": recovery, "receipt": receipt, "closer": "delivery-owner"},
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "closed"
    assert payload["closed"] is True
    assert payload["closure"]["closure_id"]


def test_v16_6_release_note_and_changelog_are_present():
    note = Path("release/V16_6_DELIVERY_RECOVERY_CLOSURE_RECORD.md").read_text(encoding="utf-8")
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert "/api/v1/case-delivery/<case_id>/recovery-closure-record" in note
    assert "v16.6 Delivery Recovery Closure Record" in changelog
