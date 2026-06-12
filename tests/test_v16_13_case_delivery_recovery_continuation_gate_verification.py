from __future__ import annotations

from pathlib import Path

from src.socmint.case_delivery_recovery_action_receipt_v16_4 import build_case_delivery_recovery_action_receipt
from src.socmint.case_delivery_recovery_closure_audit_package_v16_8 import build_case_delivery_recovery_closure_audit_package
from src.socmint.case_delivery_recovery_closure_audit_package_verification_v16_9 import verify_case_delivery_recovery_closure_audit_package
from src.socmint.case_delivery_recovery_closure_record_v16_6 import build_case_delivery_recovery_closure_record
from src.socmint.case_delivery_recovery_closure_record_verification_v16_7 import verify_case_delivery_recovery_closure_record
from src.socmint.case_delivery_recovery_continuation_gate_v16_12 import build_case_delivery_recovery_continuation_gate
from src.socmint.case_delivery_recovery_continuation_gate_verification_v16_13 import (
    CASE_DELIVERY_RECOVERY_CONTINUATION_GATE_VERIFICATION_SCHEMA,
)
from src.socmint.case_delivery_recovery_continuation_gate_verification_v16_13 import (
    verify_case_delivery_recovery_continuation_gate,
)
from src.socmint.case_delivery_recovery_finalization_record_v16_10 import build_case_delivery_recovery_finalization_record
from src.socmint.case_delivery_recovery_finalization_record_verification_v16_11 import verify_case_delivery_recovery_finalization_record
from src.socmint.case_delivery_recovery_v16_3 import build_case_delivery_recovery
from src.socmint.case_delivery_workspace_routes_v15 import register_case_delivery_workspace_routes_v15
from src.socmint.dashboard import create_app
from tests.test_v15_case_delivery_workspace import ready_payload


def _verification_artifacts():
    recovery = build_case_delivery_recovery(
        "case-v16-13-verify",
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
    receipt = build_case_delivery_recovery_action_receipt(
        "case-v16-13-verify",
        {
            "recovery": recovery,
            "operator": "delivery-lead",
            "actions": [
                {
                    "recovery_id": queue_item["recovery_id"],
                    "status": "completed",
                    "operator": "delivery-lead",
                    "detail": "Operator action completed.",
                }
            ],
        },
    )["receipt"]
    closure = build_case_delivery_recovery_closure_record(recovery, receipt, closer="delivery-owner")["closure"]
    closure_verification = verify_case_delivery_recovery_closure_record(closure, recovery, receipt)
    audit_package = build_case_delivery_recovery_closure_audit_package(
        recovery,
        receipt,
        closure,
        closure_verification,
        package_owner="auditor",
    )["audit_package"]
    audit_verification = verify_case_delivery_recovery_closure_audit_package(
        audit_package,
        recovery,
        receipt,
        closure,
        closure_verification,
    )
    finalization = build_case_delivery_recovery_finalization_record(
        recovery,
        receipt,
        closure,
        audit_package,
        audit_verification,
        finalizer="release-owner",
    )["finalization"]
    finalization_verification = verify_case_delivery_recovery_finalization_record(
        finalization,
        recovery,
        receipt,
        closure,
        audit_package,
        audit_verification,
    )
    continuation_gate = build_case_delivery_recovery_continuation_gate(
        recovery,
        receipt,
        closure,
        audit_package,
        audit_verification,
        finalization,
        finalization_verification,
        gate_operator="delivery-ops",
    )["continuation_gate"]
    return recovery, receipt, closure, audit_package, audit_verification, finalization, finalization_verification, continuation_gate


def test_case_delivery_recovery_continuation_gate_verification_passes_valid_gate():
    recovery, receipt, closure, audit_package, audit_verification, finalization, finalization_verification, gate = _verification_artifacts()

    result = verify_case_delivery_recovery_continuation_gate(
        gate,
        recovery,
        receipt,
        closure,
        audit_package,
        audit_verification,
        finalization,
        finalization_verification,
    )

    assert result["schema"] == CASE_DELIVERY_RECOVERY_CONTINUATION_GATE_VERIFICATION_SCHEMA
    assert result["status"] == "verified"
    assert result["verified"] is True
    assert result["gate_open"] is True
    assert result["ready_for_delivery_continuation"] is True
    assert result["next_action"] == "resume_delivery_operations"
    assert result["continuation_gate_id"] == gate["continuation_gate_id"]
    assert result["blocker_count"] == 0


def test_case_delivery_recovery_continuation_gate_verification_blocks_tampered_payload_hash():
    recovery, receipt, closure, audit_package, audit_verification, finalization, finalization_verification, gate = _verification_artifacts()
    tampered = {**gate, "payload_sha256": "tampered"}

    result = verify_case_delivery_recovery_continuation_gate(tampered, recovery, receipt, closure, audit_package, audit_verification, finalization, finalization_verification)

    assert result["status"] == "blocked"
    assert any(blocker["key"] == "payload_hash_mismatch" for blocker in result["blockers"])
    assert any(blocker["key"] == "continuation_gate_id_mismatch" for blocker in result["blockers"])


def test_case_delivery_recovery_continuation_gate_verification_blocks_tampered_gate_id():
    recovery, receipt, closure, audit_package, audit_verification, finalization, finalization_verification, gate = _verification_artifacts()
    tampered = {**gate, "continuation_gate_id": "tampered"}

    result = verify_case_delivery_recovery_continuation_gate(tampered, recovery, receipt, closure, audit_package, audit_verification, finalization, finalization_verification)

    assert result["status"] == "blocked"
    assert any(blocker["key"] == "continuation_gate_id_mismatch" for blocker in result["blockers"])


def test_case_delivery_recovery_continuation_gate_verification_blocks_closed_gate_flag():
    recovery, receipt, closure, audit_package, audit_verification, finalization, finalization_verification, gate = _verification_artifacts()
    tampered = {**gate, "gate_open": False}

    result = verify_case_delivery_recovery_continuation_gate(tampered, recovery, receipt, closure, audit_package, audit_verification, finalization, finalization_verification)

    assert result["status"] == "blocked"
    assert any(blocker["key"] == "gate_not_open" for blocker in result["blockers"])
    assert any(blocker["key"] == "payload_hash_mismatch" for blocker in result["blockers"])


def test_case_delivery_recovery_continuation_gate_verification_blocks_next_action_mismatch():
    recovery, receipt, closure, audit_package, audit_verification, finalization, finalization_verification, gate = _verification_artifacts()
    tampered = {**gate, "next_action": "hold_delivery"}

    result = verify_case_delivery_recovery_continuation_gate(tampered, recovery, receipt, closure, audit_package, audit_verification, finalization, finalization_verification)

    assert result["status"] == "blocked"
    assert any(blocker["key"] == "next_action_mismatch" for blocker in result["blockers"])
    assert any(blocker["key"] == "payload_hash_mismatch" for blocker in result["blockers"])


def test_case_delivery_recovery_continuation_gate_verification_route_requires_login(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_case_delivery_workspace_routes_v15(app)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["_csrf_token"] = "test-csrf"

    response = client.post(
        "/api/v1/case-delivery/case-1/recovery-continuation-gate/verify",
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert response.status_code == 401


def test_case_delivery_recovery_continuation_gate_verification_route_returns_verified(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_case_delivery_workspace_routes_v15(app)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user"] = "operator"
        sess["is_admin"] = False
        sess["_csrf_token"] = "test-csrf"

    recovery, receipt, closure, audit_package, audit_verification, finalization, finalization_verification, gate = _verification_artifacts()
    response = client.post(
        "/api/v1/case-delivery/case-1/recovery-continuation-gate/verify",
        json={
            "recovery": recovery,
            "receipt": receipt,
            "closure": closure,
            "audit_package": audit_package,
            "audit_verification": audit_verification,
            "finalization": finalization,
            "finalization_verification": finalization_verification,
            "continuation_gate": gate,
        },
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "verified"
    assert payload["verified"] is True
    assert payload["gate_open"] is True
    assert payload["continuation_gate_id"] == gate["continuation_gate_id"]


def test_v16_13_release_note_and_changelog_are_present():
    note = Path("release/V16_13_DELIVERY_RECOVERY_CONTINUATION_GATE_VERIFICATION.md").read_text(encoding="utf-8")
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert "/api/v1/case-delivery/<case_id>/recovery-continuation-gate/verify" in note
    assert "v16.13 Delivery Recovery Continuation Gate Verification" in changelog
