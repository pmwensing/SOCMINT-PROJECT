from __future__ import annotations

from pathlib import Path

from src.socmint.case_delivery_recovery_action_receipt_v16_4 import (
    build_case_delivery_recovery_action_receipt,
)
from src.socmint.case_delivery_recovery_closure_record_v16_6 import (
    build_case_delivery_recovery_closure_record,
)
from src.socmint.case_delivery_recovery_closure_record_verification_v16_7 import (
    CASE_DELIVERY_RECOVERY_CLOSURE_RECORD_VERIFICATION_SCHEMA,
)
from src.socmint.case_delivery_recovery_closure_record_verification_v16_7 import (
    verify_case_delivery_recovery_closure_record,
)
from src.socmint.case_delivery_recovery_v16_3 import build_case_delivery_recovery
from src.socmint.case_delivery_workspace_routes_v15 import (
    register_case_delivery_workspace_routes_v15,
)
from src.socmint.dashboard import create_app
from tests.test_v15_case_delivery_workspace import ready_payload


def _closed_payload(action_status: str = "completed"):
    recovery = build_case_delivery_recovery(
        "case-v16-7-verify",
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
        "case-v16-7-verify",
        {
            "recovery": recovery,
            "operator": "delivery-lead",
            "actions": [
                {
                    "recovery_id": queue_item["recovery_id"],
                    "status": action_status,
                    "operator": "delivery-lead",
                    "detail": "Operator action completed.",
                }
            ],
        },
    )
    receipt = receipt_result["receipt"]
    closure_result = build_case_delivery_recovery_closure_record(
        recovery, receipt, closer="delivery-owner"
    )
    return recovery, receipt, closure_result["closure"]


def test_case_delivery_recovery_closure_record_verification_passes_valid_closure():
    recovery, receipt, closure = _closed_payload()

    result = verify_case_delivery_recovery_closure_record(closure, recovery, receipt)

    assert result["schema"] == CASE_DELIVERY_RECOVERY_CLOSURE_RECORD_VERIFICATION_SCHEMA
    assert result["status"] == "verified"
    assert result["verified"] is True
    assert result["closure_id"] == closure["closure_id"]
    assert result["receipt_id"] == receipt["receipt_id"]
    assert result["queue_id"] == recovery["queue_id"]
    assert result["blocker_count"] == 0


def test_case_delivery_recovery_closure_record_verification_blocks_tampered_closure_id():
    recovery, receipt, closure = _closed_payload()
    tampered = {**closure, "closure_id": "tampered"}

    result = verify_case_delivery_recovery_closure_record(tampered, recovery, receipt)

    assert result["status"] == "blocked"
    assert any(
        blocker["key"] == "closure_id_mismatch" for blocker in result["blockers"]
    )


def test_case_delivery_recovery_closure_record_verification_blocks_tampered_payload_hash():
    recovery, receipt, closure = _closed_payload()
    tampered = {**closure, "payload_sha256": "tampered"}

    result = verify_case_delivery_recovery_closure_record(tampered, recovery, receipt)

    assert result["status"] == "blocked"
    assert any(
        blocker["key"] == "payload_hash_mismatch" for blocker in result["blockers"]
    )
    assert any(
        blocker["key"] == "closure_id_mismatch" for blocker in result["blockers"]
    )


def test_case_delivery_recovery_closure_record_verification_blocks_linkage_mismatch():
    recovery, receipt, closure = _closed_payload()
    tampered = {**closure, "queue_id": "other-queue"}

    result = verify_case_delivery_recovery_closure_record(tampered, recovery, receipt)

    assert result["status"] == "blocked"
    assert any(blocker["key"] == "queue_id_mismatch" for blocker in result["blockers"])
    assert any(
        blocker["key"] == "payload_hash_mismatch" for blocker in result["blockers"]
    )


def test_case_delivery_recovery_closure_record_verification_blocks_pending_receipt():
    recovery, receipt, closure = _closed_payload(action_status="pending")

    result = verify_case_delivery_recovery_closure_record(closure, recovery, receipt)

    assert result["status"] == "blocked"
    assert any(
        blocker["key"] in {"missing_closure", "receipt_not_complete"}
        for blocker in result["blockers"]
    )


def test_case_delivery_recovery_closure_record_verification_route_requires_login(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_case_delivery_workspace_routes_v15(app)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["_csrf_token"] = "test-csrf"

    response = client.post(
        "/api/v1/case-delivery/case-1/recovery-closure-record/verify",
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert response.status_code == 401


def test_case_delivery_recovery_closure_record_verification_route_returns_verified(
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

    recovery, receipt, closure = _closed_payload()
    response = client.post(
        "/api/v1/case-delivery/case-1/recovery-closure-record/verify",
        json={"recovery": recovery, "receipt": receipt, "closure": closure},
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "verified"
    assert payload["verified"] is True
    assert payload["closure_id"] == closure["closure_id"]


def test_v16_7_release_note_and_changelog_are_present():
    note = Path(
        "release/V16_7_DELIVERY_RECOVERY_CLOSURE_RECORD_VERIFICATION.md"
    ).read_text(encoding="utf-8")
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert "/api/v1/case-delivery/<case_id>/recovery-closure-record/verify" in note
    assert "v16.7 Delivery Recovery Closure Record Verification" in changelog
