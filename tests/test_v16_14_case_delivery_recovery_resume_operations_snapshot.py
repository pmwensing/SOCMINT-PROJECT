from __future__ import annotations

from pathlib import Path

from src.socmint.case_delivery_recovery_action_receipt_v16_4 import build_case_delivery_recovery_action_receipt
from src.socmint.case_delivery_recovery_closure_audit_package_v16_8 import build_case_delivery_recovery_closure_audit_package
from src.socmint.case_delivery_recovery_closure_audit_package_verification_v16_9 import verify_case_delivery_recovery_closure_audit_package
from src.socmint.case_delivery_recovery_closure_record_v16_6 import build_case_delivery_recovery_closure_record
from src.socmint.case_delivery_recovery_closure_record_verification_v16_7 import verify_case_delivery_recovery_closure_record
from src.socmint.case_delivery_recovery_continuation_gate_v16_12 import build_case_delivery_recovery_continuation_gate
from src.socmint.case_delivery_recovery_continuation_gate_verification_v16_13 import verify_case_delivery_recovery_continuation_gate
from src.socmint.case_delivery_recovery_finalization_record_v16_10 import build_case_delivery_recovery_finalization_record
from src.socmint.case_delivery_recovery_finalization_record_verification_v16_11 import verify_case_delivery_recovery_finalization_record
from src.socmint.case_delivery_recovery_resume_operations_snapshot_v16_14 import (
    CASE_DELIVERY_RECOVERY_RESUME_OPERATIONS_SNAPSHOT_SCHEMA,
)
from src.socmint.case_delivery_recovery_resume_operations_snapshot_v16_14 import (
    build_case_delivery_recovery_resume_operations_snapshot,
)
from src.socmint.case_delivery_recovery_v16_3 import build_case_delivery_recovery
from src.socmint.case_delivery_workspace_routes_v15 import register_case_delivery_workspace_routes_v15
from src.socmint.dashboard import create_app
from tests.test_v15_case_delivery_workspace import ready_payload


def _resume_artifacts():
    recovery = build_case_delivery_recovery(
        "case-v16-14-resume",
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
        "case-v16-14-resume",
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
    continuation_gate_verification = verify_case_delivery_recovery_continuation_gate(
        continuation_gate,
        recovery,
        receipt,
        closure,
        audit_package,
        audit_verification,
        finalization,
        finalization_verification,
    )
    return (
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


def test_case_delivery_recovery_resume_operations_snapshot_marks_ready():
    artifacts = _resume_artifacts()

    result = build_case_delivery_recovery_resume_operations_snapshot(*artifacts, resume_operator="delivery-ops")

    assert result["status"] == "ready"
    assert result["safe_to_reenter_operations"] is True
    assert result["next_action"] == "execute_delivery_operations"
    snapshot = result["resume_snapshot"]
    assert snapshot["schema"] == CASE_DELIVERY_RECOVERY_RESUME_OPERATIONS_SNAPSHOT_SCHEMA
    assert snapshot["resume_operator"] == "delivery-ops"
    assert snapshot["safe_to_reenter_operations"] is True
    assert snapshot["resume_snapshot_id"]
    assert result["blocker_count"] == 0


def test_case_delivery_recovery_resume_operations_snapshot_id_is_deterministic_and_operator_sensitive():
    artifacts = _resume_artifacts()

    first = build_case_delivery_recovery_resume_operations_snapshot(*artifacts, resume_operator="delivery-ops")
    second = build_case_delivery_recovery_resume_operations_snapshot(*artifacts, resume_operator="delivery-ops")
    changed = build_case_delivery_recovery_resume_operations_snapshot(*artifacts, resume_operator="other-ops")

    assert first["resume_snapshot"]["resume_snapshot_id"] == second["resume_snapshot"]["resume_snapshot_id"]
    assert first["resume_snapshot"]["resume_snapshot_id"] != changed["resume_snapshot"]["resume_snapshot_id"]


def test_case_delivery_recovery_resume_operations_snapshot_blocks_failed_gate_verification():
    artifacts = list(_resume_artifacts())
    artifacts[-1] = {"status": "blocked", "verified": False, "gate_open": False, "ready_for_delivery_continuation": False, "blockers": [{"key": "tampered", "detail": "tampered"}]}

    result = build_case_delivery_recovery_resume_operations_snapshot(*artifacts, resume_operator="delivery-ops")

    assert result["status"] == "blocked"
    assert result["safe_to_reenter_operations"] is False
    assert result["resume_snapshot"] is None
    assert result["next_action"] == "resolve_recovery_continuation_gate"
    assert any(blocker["key"] == "continuation_gate_verification_blocked" for blocker in result["blockers"])


def test_case_delivery_recovery_resume_operations_snapshot_blocks_linkage_mismatch():
    artifacts = list(_resume_artifacts())
    artifacts[-2] = {**artifacts[-2], "continuation_gate_id": "other-gate"}

    result = build_case_delivery_recovery_resume_operations_snapshot(*artifacts, resume_operator="delivery-ops")

    assert result["status"] == "blocked"
    assert any(blocker["key"] == "continuation_gate_id_mismatch" for blocker in result["blockers"])


def test_case_delivery_recovery_resume_operations_snapshot_route_requires_login(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_case_delivery_workspace_routes_v15(app)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["_csrf_token"] = "test-csrf"

    response = client.post(
        "/api/v1/case-delivery/case-1/recovery-resume-operations-snapshot",
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert response.status_code == 401


def test_case_delivery_recovery_resume_operations_snapshot_route_returns_ready(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_case_delivery_workspace_routes_v15(app)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user"] = "operator"
        sess["is_admin"] = False
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
    ) = _resume_artifacts()
    response = client.post(
        "/api/v1/case-delivery/case-1/recovery-resume-operations-snapshot",
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
            "resume_operator": "delivery-ops",
        },
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ready"
    assert payload["safe_to_reenter_operations"] is True
    assert payload["next_action"] == "execute_delivery_operations"
    assert payload["resume_snapshot"]["resume_snapshot_id"]


def test_v16_14_release_note_and_changelog_are_present():
    note = Path("release/V16_14_DELIVERY_RECOVERY_RESUME_OPERATIONS_SNAPSHOT.md").read_text(encoding="utf-8")
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert "/api/v1/case-delivery/<case_id>/recovery-resume-operations-snapshot" in note
    assert "v16.14 Delivery Recovery Resume Operations Snapshot" in changelog
