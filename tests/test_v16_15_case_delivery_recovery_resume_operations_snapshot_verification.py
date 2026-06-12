from __future__ import annotations

from pathlib import Path

from src.socmint.case_delivery_recovery_continuation_gate_verification_v16_13 import verify_case_delivery_recovery_continuation_gate
from src.socmint.case_delivery_recovery_resume_operations_snapshot_v16_14 import build_case_delivery_recovery_resume_operations_snapshot
from src.socmint.case_delivery_recovery_resume_operations_snapshot_verification_v16_15 import (
    CASE_DELIVERY_RECOVERY_RESUME_OPERATIONS_SNAPSHOT_VERIFICATION_SCHEMA,
    verify_case_delivery_recovery_resume_operations_snapshot,
)
from src.socmint.case_delivery_workspace_routes_v15 import register_case_delivery_workspace_routes_v15
from src.socmint.dashboard import create_app
from tests.test_v16_14_case_delivery_recovery_resume_operations_snapshot import _resume_artifacts


def _artifacts_with_snapshot():
    artifacts = _resume_artifacts()
    snapshot = build_case_delivery_recovery_resume_operations_snapshot(*artifacts, resume_operator="delivery-ops")["resume_snapshot"]
    return (*artifacts, snapshot)


def test_v16_15_verifies_valid_resume_snapshot():
    recovery, receipt, closure, audit_package, audit_verification, finalization, finalization_verification, continuation_gate, continuation_gate_verification, snapshot = _artifacts_with_snapshot()

    result = verify_case_delivery_recovery_resume_operations_snapshot(
        snapshot,
        recovery,
        receipt,
        closure,
        audit_package,
        audit_verification,
        finalization,
        finalization_verification,
        continuation_gate,
        continuation_gate_verification,
    )

    assert result["schema"] == CASE_DELIVERY_RECOVERY_RESUME_OPERATIONS_SNAPSHOT_VERIFICATION_SCHEMA
    assert result["status"] == "verified"
    assert result["verified"] is True
    assert result["safe_to_reenter_operations"] is True
    assert result["next_action"] == "execute_delivery_operations"
    assert result["resume_snapshot_id"] == snapshot["resume_snapshot_id"]


def test_v16_15_blocks_tampered_resume_snapshot_hash_and_id():
    recovery, receipt, closure, audit_package, audit_verification, finalization, finalization_verification, continuation_gate, continuation_gate_verification, snapshot = _artifacts_with_snapshot()
    tampered = {**snapshot, "payload_sha256": "tampered"}

    result = verify_case_delivery_recovery_resume_operations_snapshot(
        tampered,
        recovery,
        receipt,
        closure,
        audit_package,
        audit_verification,
        finalization,
        finalization_verification,
        continuation_gate,
        continuation_gate_verification,
    )

    assert result["status"] == "blocked"
    assert any(blocker["key"] == "payload_hash_mismatch" for blocker in result["blockers"])
    assert any(blocker["key"] == "resume_snapshot_id_mismatch" for blocker in result["blockers"])


def test_v16_15_blocks_unsafe_resume_and_wrong_next_action():
    recovery, receipt, closure, audit_package, audit_verification, finalization, finalization_verification, continuation_gate, continuation_gate_verification, snapshot = _artifacts_with_snapshot()
    tampered = {**snapshot, "safe_to_reenter_operations": False, "next_action": "hold_delivery"}

    result = verify_case_delivery_recovery_resume_operations_snapshot(
        tampered,
        recovery,
        receipt,
        closure,
        audit_package,
        audit_verification,
        finalization,
        finalization_verification,
        continuation_gate,
        continuation_gate_verification,
    )

    assert result["status"] == "blocked"
    assert any(blocker["key"] == "not_safe_to_reenter_operations" for blocker in result["blockers"])
    assert any(blocker["key"] == "next_action_mismatch" for blocker in result["blockers"])


def test_v16_15_route_requires_login(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_case_delivery_workspace_routes_v15(app)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["_csrf_token"] = "test-csrf"

    response = client.post(
        "/api/v1/case-delivery/case-1/recovery-resume-operations-snapshot/verify",
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert response.status_code == 401


def test_v16_15_route_returns_verified(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_case_delivery_workspace_routes_v15(app)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user"] = "operator"
        sess["_csrf_token"] = "test-csrf"

    recovery, receipt, closure, audit_package, audit_verification, finalization, finalization_verification, continuation_gate, continuation_gate_verification, snapshot = _artifacts_with_snapshot()
    response = client.post(
        "/api/v1/case-delivery/case-1/recovery-resume-operations-snapshot/verify",
        json={
            "recovery": recovery,
            "receipt": receipt,
            "closure": closure,
            "audit_package": audit_package,
            "audit_verification": audit_verification,
            "finalization": finalization,
            "finalization_verification": finalization_verification,
            "continuation_gate": continuation_gate,
            "continuation_gate_verification": continuation_gate_verification,
            "resume_snapshot": snapshot,
        },
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "verified"
    assert payload["safe_to_reenter_operations"] is True
    assert payload["resume_snapshot_id"] == snapshot["resume_snapshot_id"]


def test_v16_15_release_note_and_changelog_are_present():
    note = Path("release/V16_15_DELIVERY_RECOVERY_RESUME_OPERATIONS_SNAPSHOT_VERIFICATION.md").read_text(encoding="utf-8")
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert "/api/v1/case-delivery/<case_id>/recovery-resume-operations-snapshot/verify" in note
    assert "v16.15 Delivery Recovery Resume Operations Snapshot Verification" in changelog
