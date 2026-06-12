from __future__ import annotations

from pathlib import Path

from src.socmint.case_delivery_operations_reentry_envelope_v16_16 import build_case_delivery_operations_reentry_envelope
from src.socmint.case_delivery_operations_reentry_envelope_verification_v16_17 import (
    CASE_DELIVERY_OPERATIONS_REENTRY_ENVELOPE_VERIFICATION_SCHEMA,
    verify_case_delivery_operations_reentry_envelope,
)
from src.socmint.case_delivery_recovery_resume_operations_snapshot_verification_v16_15 import verify_case_delivery_recovery_resume_operations_snapshot
from src.socmint.case_delivery_workspace_routes_v15 import register_case_delivery_workspace_routes_v15
from src.socmint.dashboard import create_app
from tests.test_v16_15_case_delivery_recovery_resume_operations_snapshot_verification import _artifacts_with_snapshot


def _verification_artifacts():
    base = _artifacts_with_snapshot()
    resume_snapshot_verification = verify_case_delivery_recovery_resume_operations_snapshot(base[-1], *base[:-1])
    envelope = build_case_delivery_operations_reentry_envelope(*base, resume_snapshot_verification, reentry_operator="delivery-ops")["reentry_envelope"]
    return (*base, resume_snapshot_verification, envelope)


def test_v16_17_verifies_valid_reentry_envelope():
    recovery, receipt, closure, audit_package, audit_verification, finalization, finalization_verification, continuation_gate, continuation_gate_verification, resume_snapshot, resume_snapshot_verification, envelope = _verification_artifacts()

    result = verify_case_delivery_operations_reentry_envelope(
        envelope,
        recovery,
        receipt,
        closure,
        audit_package,
        audit_verification,
        finalization,
        finalization_verification,
        continuation_gate,
        continuation_gate_verification,
        resume_snapshot,
        resume_snapshot_verification,
    )

    assert result["schema"] == CASE_DELIVERY_OPERATIONS_REENTRY_ENVELOPE_VERIFICATION_SCHEMA
    assert result["status"] == "verified"
    assert result["verified"] is True
    assert result["ready_for_operations_dispatch"] is True
    assert result["next_action"] == "dispatch_delivery_operations"
    assert result["reentry_envelope_id"] == envelope["reentry_envelope_id"]


def test_v16_17_blocks_tampered_payload_hash_and_envelope_id():
    artifacts = list(_verification_artifacts())
    artifacts[-1] = {**artifacts[-1], "payload_sha256": "tampered"}

    result = verify_case_delivery_operations_reentry_envelope(artifacts[-1], *artifacts[:-1])

    assert result["status"] == "blocked"
    assert any(blocker["key"] == "payload_hash_mismatch" for blocker in result["blockers"])
    assert any(blocker["key"] == "reentry_envelope_id_mismatch" for blocker in result["blockers"])


def test_v16_17_blocks_not_ready_and_next_action_mismatch():
    artifacts = list(_verification_artifacts())
    artifacts[-1] = {**artifacts[-1], "ready_for_operations_dispatch": False, "next_action": "hold_delivery"}

    result = verify_case_delivery_operations_reentry_envelope(artifacts[-1], *artifacts[:-1])

    assert result["status"] == "blocked"
    assert any(blocker["key"] == "not_ready_for_operations_dispatch" for blocker in result["blockers"])
    assert any(blocker["key"] == "next_action_mismatch" for blocker in result["blockers"])


def test_v16_17_route_requires_login(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_case_delivery_workspace_routes_v15(app)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["_csrf_token"] = "test-csrf"

    response = client.post(
        "/api/v1/case-delivery/case-1/operations-reentry-envelope/verify",
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert response.status_code == 401


def test_v16_17_route_returns_verified(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_case_delivery_workspace_routes_v15(app)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user"] = "operator"
        sess["_csrf_token"] = "test-csrf"

    recovery, receipt, closure, audit_package, audit_verification, finalization, finalization_verification, continuation_gate, continuation_gate_verification, resume_snapshot, resume_snapshot_verification, envelope = _verification_artifacts()
    response = client.post(
        "/api/v1/case-delivery/case-1/operations-reentry-envelope/verify",
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
            "resume_snapshot": resume_snapshot,
            "resume_snapshot_verification": resume_snapshot_verification,
            "reentry_envelope": envelope,
        },
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "verified"
    assert payload["ready_for_operations_dispatch"] is True
    assert payload["reentry_envelope_id"] == envelope["reentry_envelope_id"]


def test_v16_17_release_note_and_changelog_are_present():
    note = Path("release/V16_17_DELIVERY_OPERATIONS_REENTRY_ENVELOPE_VERIFICATION.md").read_text(encoding="utf-8")
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert "/api/v1/case-delivery/<case_id>/operations-reentry-envelope/verify" in note
    assert "v16.17 Delivery Operations Re-Entry Envelope Verification" in changelog
