from __future__ import annotations

from pathlib import Path

from src.socmint.case_delivery_recovery_action_receipt_v16_4 import (
    build_case_delivery_recovery_action_receipt,
)
from src.socmint.case_delivery_recovery_closure_audit_package_v16_8 import (
    build_case_delivery_recovery_closure_audit_package,
)
from src.socmint.case_delivery_recovery_closure_audit_package_verification_v16_9 import (
    verify_case_delivery_recovery_closure_audit_package,
)
from src.socmint.case_delivery_recovery_closure_record_v16_6 import (
    build_case_delivery_recovery_closure_record,
)
from src.socmint.case_delivery_recovery_closure_record_verification_v16_7 import (
    verify_case_delivery_recovery_closure_record,
)
from src.socmint.case_delivery_recovery_finalization_record_v16_10 import (
    CASE_DELIVERY_RECOVERY_FINALIZATION_RECORD_SCHEMA,
)
from src.socmint.case_delivery_recovery_finalization_record_v16_10 import (
    build_case_delivery_recovery_finalization_record,
)
from src.socmint.case_delivery_recovery_v16_3 import build_case_delivery_recovery
from src.socmint.case_delivery_workspace_routes_v15 import (
    register_case_delivery_workspace_routes_v15,
)
from src.socmint.dashboard import create_app
from tests.test_v15_case_delivery_workspace import ready_payload


def _finalization_artifacts():
    recovery = build_case_delivery_recovery(
        "case-v16-10-finalize",
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
        "case-v16-10-finalize",
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
    closure = build_case_delivery_recovery_closure_record(
        recovery, receipt, closer="delivery-owner"
    )["closure"]
    closure_verification = verify_case_delivery_recovery_closure_record(
        closure, recovery, receipt
    )
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
    return recovery, receipt, closure, audit_package, audit_verification


def test_case_delivery_recovery_finalization_record_finalizes_verified_audit_package():
    recovery, receipt, closure, audit_package, audit_verification = (
        _finalization_artifacts()
    )

    result = build_case_delivery_recovery_finalization_record(
        recovery,
        receipt,
        closure,
        audit_package,
        audit_verification,
        finalizer="release-owner",
    )

    assert result["status"] == "finalized"
    assert result["finalized"] is True
    assert result["ready_for_delivery_continuation"] is True
    assert result["next_action"] == "continue_delivery"
    finalization = result["finalization"]
    assert finalization["schema"] == CASE_DELIVERY_RECOVERY_FINALIZATION_RECORD_SCHEMA
    assert finalization["finalized"] is True
    assert finalization["ready_for_delivery_continuation"] is True
    assert finalization["finalized_by"] == "release-owner"
    assert finalization["audit_package_id"] == audit_package["audit_package_id"]
    assert finalization["finalization_id"]
    assert result["blocker_count"] == 0


def test_case_delivery_recovery_finalization_record_id_is_deterministic_and_finalizer_sensitive():
    recovery, receipt, closure, audit_package, audit_verification = (
        _finalization_artifacts()
    )

    first = build_case_delivery_recovery_finalization_record(
        recovery,
        receipt,
        closure,
        audit_package,
        audit_verification,
        finalizer="release-owner",
    )
    second = build_case_delivery_recovery_finalization_record(
        recovery,
        receipt,
        closure,
        audit_package,
        audit_verification,
        finalizer="release-owner",
    )
    changed = build_case_delivery_recovery_finalization_record(
        recovery,
        receipt,
        closure,
        audit_package,
        audit_verification,
        finalizer="other-owner",
    )

    assert (
        first["finalization"]["finalization_id"]
        == second["finalization"]["finalization_id"]
    )
    assert (
        first["finalization"]["finalization_id"]
        != changed["finalization"]["finalization_id"]
    )


def test_case_delivery_recovery_finalization_record_blocks_failed_audit_verification():
    recovery, receipt, closure, audit_package, _audit_verification = (
        _finalization_artifacts()
    )
    failed_verification = {
        "status": "blocked",
        "verified": False,
        "blockers": [{"key": "tampered", "detail": "tampered"}],
    }

    result = build_case_delivery_recovery_finalization_record(
        recovery,
        receipt,
        closure,
        audit_package,
        failed_verification,
        finalizer="release-owner",
    )

    assert result["status"] == "blocked"
    assert result["finalized"] is False
    assert result["ready_for_delivery_continuation"] is False
    assert result["finalization"] is None
    assert any(
        blocker["key"] == "audit_verification_blocked" for blocker in result["blockers"]
    )


def test_case_delivery_recovery_finalization_record_blocks_linkage_mismatch():
    recovery, receipt, closure, audit_package, audit_verification = (
        _finalization_artifacts()
    )
    tampered_package = {**audit_package, "receipt_id": "other-receipt"}

    result = build_case_delivery_recovery_finalization_record(
        recovery,
        receipt,
        closure,
        tampered_package,
        audit_verification,
        finalizer="release-owner",
    )

    assert result["status"] == "blocked"
    assert any(
        blocker["key"] == "audit_package_receipt_mismatch"
        for blocker in result["blockers"]
    )


def test_case_delivery_recovery_finalization_record_route_requires_login(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_case_delivery_workspace_routes_v15(app)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["_csrf_token"] = "test-csrf"

    response = client.post(
        "/api/v1/case-delivery/case-1/recovery-finalization-record",
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert response.status_code == 401


def test_case_delivery_recovery_finalization_record_route_returns_finalized(
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

    recovery, receipt, closure, audit_package, audit_verification = (
        _finalization_artifacts()
    )
    response = client.post(
        "/api/v1/case-delivery/case-1/recovery-finalization-record",
        json={
            "recovery": recovery,
            "receipt": receipt,
            "closure": closure,
            "audit_package": audit_package,
            "audit_verification": audit_verification,
            "finalizer": "release-owner",
        },
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "finalized"
    assert payload["finalized"] is True
    assert payload["ready_for_delivery_continuation"] is True
    assert payload["finalization"]["finalization_id"]


def test_v16_10_release_note_and_changelog_are_present():
    note = Path("release/V16_10_DELIVERY_RECOVERY_FINALIZATION_RECORD.md").read_text(
        encoding="utf-8"
    )
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert "/api/v1/case-delivery/<case_id>/recovery-finalization-record" in note
    assert "v16.10 Delivery Recovery Finalization Record" in changelog
