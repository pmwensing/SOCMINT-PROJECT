from __future__ import annotations

from pathlib import Path

from src.socmint.case_delivery_operations_reentry_envelope_v16_16 import CASE_DELIVERY_OPERATIONS_REENTRY_ENVELOPE_SCHEMA
from src.socmint.case_delivery_operations_reentry_envelope_v16_16 import build_case_delivery_operations_reentry_envelope
from src.socmint.case_delivery_recovery_resume_operations_snapshot_verification_v16_15 import (
    verify_case_delivery_recovery_resume_operations_snapshot,
)
from src.socmint.case_delivery_workspace_routes_v15 import register_case_delivery_workspace_routes_v15
from src.socmint.dashboard import create_app
from tests.test_v16_15_case_delivery_recovery_resume_operations_snapshot_verification import _artifacts_with_snapshot


def _reentry_artifacts():
    artifacts = _artifacts_with_snapshot()
    resume_verification = verify_case_delivery_recovery_resume_operations_snapshot(artifacts[-1], *artifacts[:-1])
    return (*artifacts, resume_verification)


def test_v16_16_builds_ready_reentry_envelope():
    artifacts = _reentry_artifacts()

    result = build_case_delivery_operations_reentry_envelope(*artifacts, reentry_operator="delivery-ops")

    assert result["status"] == "ready_to_dispatch"
    assert result["ready_for_operations_dispatch"] is True
    assert result["next_action"] == "dispatch_delivery_operations"
    envelope = result["reentry_envelope"]
    assert envelope["schema"] == CASE_DELIVERY_OPERATIONS_REENTRY_ENVELOPE_SCHEMA
    assert envelope["reentry_operator"] == "delivery-ops"
    assert envelope["ready_for_operations_dispatch"] is True
    assert envelope["reentry_envelope_id"]
    assert result["blocker_count"] == 0


def test_v16_16_reentry_envelope_id_is_deterministic_and_operator_sensitive():
    artifacts = _reentry_artifacts()

    first = build_case_delivery_operations_reentry_envelope(*artifacts, reentry_operator="delivery-ops")
    second = build_case_delivery_operations_reentry_envelope(*artifacts, reentry_operator="delivery-ops")
    changed = build_case_delivery_operations_reentry_envelope(*artifacts, reentry_operator="other-ops")

    assert first["reentry_envelope"]["reentry_envelope_id"] == second["reentry_envelope"]["reentry_envelope_id"]
    assert first["reentry_envelope"]["reentry_envelope_id"] != changed["reentry_envelope"]["reentry_envelope_id"]


def test_v16_16_blocks_failed_resume_snapshot_verification():
    artifacts = list(_reentry_artifacts())
    artifacts[-1] = {"status": "blocked", "verified": False, "safe_to_reenter_operations": False, "next_action": "resolve_recovery_resume_snapshot", "blockers": [{"key": "tampered", "detail": "tampered"}]}

    result = build_case_delivery_operations_reentry_envelope(*artifacts, reentry_operator="delivery-ops")

    assert result["status"] == "blocked"
    assert result["ready_for_operations_dispatch"] is False
    assert result["reentry_envelope"] is None
    assert result["next_action"] == "resolve_recovery_resume_snapshot"
    assert any(blocker["key"] == "resume_snapshot_verification_blocked" for blocker in result["blockers"])


def test_v16_16_blocks_resume_snapshot_id_mismatch():
    artifacts = list(_reentry_artifacts())
    artifacts[-2] = {**artifacts[-2], "resume_snapshot_id": "other-snapshot"}

    result = build_case_delivery_operations_reentry_envelope(*artifacts, reentry_operator="delivery-ops")

    assert result["status"] == "blocked"
    assert any(blocker["key"] == "resume_snapshot_id_mismatch" for blocker in result["blockers"])


def test_v16_16_route_requires_login(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_case_delivery_workspace_routes_v15(app)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["_csrf_token"] = "test-csrf"

    response = client.post(
        "/api/v1/case-delivery/case-1/operations-reentry-envelope",
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert response.status_code == 401


def test_v16_16_route_returns_ready_to_dispatch(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_case_delivery_workspace_routes_v15(app)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user"] = "operator"
        sess["_csrf_token"] = "test-csrf"

    (
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
    ) = _reentry_artifacts()
    response = client.post(
        "/api/v1/case-delivery/case-1/operations-reentry-envelope",
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
            "reentry_operator": "delivery-ops",
        },
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ready_to_dispatch"
    assert payload["ready_for_operations_dispatch"] is True
    assert payload["next_action"] == "dispatch_delivery_operations"
    assert payload["reentry_envelope"]["reentry_envelope_id"]


def test_v16_16_release_note_and_changelog_are_present():
    note = Path("release/V16_16_DELIVERY_OPERATIONS_REENTRY_ENVELOPE.md").read_text(encoding="utf-8")
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert "/api/v1/case-delivery/<case_id>/operations-reentry-envelope" in note
    assert "v16.16 Delivery Operations Re-Entry Envelope" in changelog
