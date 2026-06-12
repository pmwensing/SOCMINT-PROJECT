from __future__ import annotations

from pathlib import Path

from src.socmint.case_delivery_recovery_action_receipt_v16_4 import build_case_delivery_recovery_action_receipt
from src.socmint.case_delivery_recovery_closure_audit_package_v16_8 import build_case_delivery_recovery_closure_audit_package
from src.socmint.case_delivery_recovery_closure_audit_package_verification_v16_9 import (
    CASE_DELIVERY_RECOVERY_CLOSURE_AUDIT_PACKAGE_VERIFICATION_SCHEMA,
)
from src.socmint.case_delivery_recovery_closure_audit_package_verification_v16_9 import (
    verify_case_delivery_recovery_closure_audit_package,
)
from src.socmint.case_delivery_recovery_closure_record_v16_6 import build_case_delivery_recovery_closure_record
from src.socmint.case_delivery_recovery_closure_record_verification_v16_7 import verify_case_delivery_recovery_closure_record
from src.socmint.case_delivery_recovery_v16_3 import build_case_delivery_recovery
from src.socmint.case_delivery_workspace_routes_v15 import register_case_delivery_workspace_routes_v15
from src.socmint.dashboard import create_app
from tests.test_v15_case_delivery_workspace import ready_payload


def _audit_artifacts():
    recovery = build_case_delivery_recovery(
        "case-v16-9-verify",
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
        "case-v16-9-verify",
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
    return recovery, receipt, closure, closure_verification, audit_package


def test_case_delivery_recovery_closure_audit_package_verification_passes_valid_package():
    recovery, receipt, closure, closure_verification, audit_package = _audit_artifacts()

    result = verify_case_delivery_recovery_closure_audit_package(
        audit_package,
        recovery,
        receipt,
        closure,
        closure_verification,
    )

    assert result["schema"] == CASE_DELIVERY_RECOVERY_CLOSURE_AUDIT_PACKAGE_VERIFICATION_SCHEMA
    assert result["status"] == "verified"
    assert result["verified"] is True
    assert result["audit_package_id"] == audit_package["audit_package_id"]
    assert result["queue_id"] == recovery["queue_id"]
    assert result["blocker_count"] == 0


def test_case_delivery_recovery_closure_audit_package_verification_blocks_tampered_package_hash():
    recovery, receipt, closure, closure_verification, audit_package = _audit_artifacts()
    tampered = {**audit_package, "package_sha256": "tampered"}

    result = verify_case_delivery_recovery_closure_audit_package(tampered, recovery, receipt, closure, closure_verification)

    assert result["status"] == "blocked"
    assert any(blocker["key"] == "package_hash_mismatch" for blocker in result["blockers"])
    assert any(blocker["key"] == "audit_package_id_mismatch" for blocker in result["blockers"])


def test_case_delivery_recovery_closure_audit_package_verification_blocks_tampered_package_id():
    recovery, receipt, closure, closure_verification, audit_package = _audit_artifacts()
    tampered = {**audit_package, "audit_package_id": "tampered"}

    result = verify_case_delivery_recovery_closure_audit_package(tampered, recovery, receipt, closure, closure_verification)

    assert result["status"] == "blocked"
    assert any(blocker["key"] == "audit_package_id_mismatch" for blocker in result["blockers"])


def test_case_delivery_recovery_closure_audit_package_verification_blocks_manifest_tampering():
    recovery, receipt, closure, closure_verification, audit_package = _audit_artifacts()
    tampered_manifest = [{**row} for row in audit_package["manifest"]]
    tampered_manifest[0]["sha256"] = "tampered"
    tampered = {**audit_package, "manifest": tampered_manifest}

    result = verify_case_delivery_recovery_closure_audit_package(tampered, recovery, receipt, closure, closure_verification)

    assert result["status"] == "blocked"
    assert any(blocker["key"] == "manifest_sha256_mismatch" for blocker in result["blockers"])
    assert any(blocker["key"] == "manifest_id_mismatch" for blocker in result["blockers"])
    assert any(blocker["key"] == "package_hash_mismatch" for blocker in result["blockers"])


def test_case_delivery_recovery_closure_audit_package_verification_blocks_linkage_mismatch():
    recovery, receipt, closure, closure_verification, audit_package = _audit_artifacts()
    tampered = {**audit_package, "queue_id": "other-queue"}

    result = verify_case_delivery_recovery_closure_audit_package(tampered, recovery, receipt, closure, closure_verification)

    assert result["status"] == "blocked"
    assert any(blocker["key"] == "queue_id_mismatch" for blocker in result["blockers"])
    assert any(blocker["key"] == "package_hash_mismatch" for blocker in result["blockers"])


def test_case_delivery_recovery_closure_audit_package_verification_route_requires_login(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_case_delivery_workspace_routes_v15(app)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["_csrf_token"] = "test-csrf"

    response = client.post(
        "/api/v1/case-delivery/case-1/recovery-closure-audit-package/verify",
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert response.status_code == 401


def test_case_delivery_recovery_closure_audit_package_verification_route_returns_verified(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_case_delivery_workspace_routes_v15(app)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user"] = "operator"
        sess["is_admin"] = False
        sess["_csrf_token"] = "test-csrf"

    recovery, receipt, closure, closure_verification, audit_package = _audit_artifacts()
    response = client.post(
        "/api/v1/case-delivery/case-1/recovery-closure-audit-package/verify",
        json={
            "recovery": recovery,
            "receipt": receipt,
            "closure": closure,
            "closure_verification": closure_verification,
            "audit_package": audit_package,
        },
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "verified"
    assert payload["verified"] is True
    assert payload["audit_package_id"] == audit_package["audit_package_id"]


def test_v16_9_release_note_and_changelog_are_present():
    note = Path("release/V16_9_DELIVERY_RECOVERY_CLOSURE_AUDIT_PACKAGE_VERIFICATION.md").read_text(encoding="utf-8")
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert "/api/v1/case-delivery/<case_id>/recovery-closure-audit-package/verify" in note
    assert "v16.9 Delivery Recovery Closure Audit Package Verification" in changelog
