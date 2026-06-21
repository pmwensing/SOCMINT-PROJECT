from __future__ import annotations

from pathlib import Path

from src.socmint.case_delivery_recovery_action_receipt_v16_4 import (
    build_case_delivery_recovery_action_receipt,
)
from src.socmint.case_delivery_recovery_closure_audit_package_v16_8 import (
    CASE_DELIVERY_RECOVERY_CLOSURE_AUDIT_PACKAGE_SCHEMA,
)
from src.socmint.case_delivery_recovery_closure_audit_package_v16_8 import (
    build_case_delivery_recovery_closure_audit_package,
)
from src.socmint.case_delivery_recovery_closure_record_v16_6 import (
    build_case_delivery_recovery_closure_record,
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


def _package_artifacts(action_status: str = "completed"):
    recovery = build_case_delivery_recovery(
        "case-v16-8-package",
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
        "case-v16-8-package",
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
    closure = closure_result["closure"]
    closure_verification = verify_case_delivery_recovery_closure_record(
        closure, recovery, receipt
    )
    return recovery, receipt, closure, closure_verification


def test_case_delivery_recovery_closure_audit_package_builds_verified_package():
    recovery, receipt, closure, closure_verification = _package_artifacts()

    result = build_case_delivery_recovery_closure_audit_package(
        recovery,
        receipt,
        closure,
        closure_verification,
        package_owner="auditor",
    )

    assert result["status"] == "packaged"
    assert result["packaged"] is True
    package = result["audit_package"]
    assert package["schema"] == CASE_DELIVERY_RECOVERY_CLOSURE_AUDIT_PACKAGE_SCHEMA
    assert package["verified"] is True
    assert package["package_owner"] == "auditor"
    assert package["artifact_count"] == 4
    assert package["audit_package_id"]
    assert [row["name"] for row in package["manifest"]] == [
        "recovery",
        "receipt",
        "closure",
        "closure_verification",
    ]
    assert all(row["present"] is True for row in package["manifest"])
    assert result["blocker_count"] == 0


def test_case_delivery_recovery_closure_audit_package_id_is_deterministic_and_owner_sensitive():
    recovery, receipt, closure, closure_verification = _package_artifacts()

    first = build_case_delivery_recovery_closure_audit_package(
        recovery,
        receipt,
        closure,
        closure_verification,
        package_owner="auditor",
    )
    second = build_case_delivery_recovery_closure_audit_package(
        recovery,
        receipt,
        closure,
        closure_verification,
        package_owner="auditor",
    )
    changed = build_case_delivery_recovery_closure_audit_package(
        recovery,
        receipt,
        closure,
        closure_verification,
        package_owner="other-auditor",
    )

    assert (
        first["audit_package"]["audit_package_id"]
        == second["audit_package"]["audit_package_id"]
    )
    assert (
        first["audit_package"]["audit_package_id"]
        != changed["audit_package"]["audit_package_id"]
    )


def test_case_delivery_recovery_closure_audit_package_blocks_failed_closure_verification():
    recovery, receipt, closure, _closure_verification = _package_artifacts()
    tampered_verification = {
        "status": "blocked",
        "verified": False,
        "blockers": [{"key": "tampered", "detail": "tampered"}],
    }

    result = build_case_delivery_recovery_closure_audit_package(
        recovery,
        receipt,
        closure,
        tampered_verification,
        package_owner="auditor",
    )

    assert result["status"] == "blocked"
    assert result["packaged"] is False
    assert result["audit_package"] is None
    assert any(
        blocker["key"] == "closure_verification_blocked"
        for blocker in result["blockers"]
    )


def test_case_delivery_recovery_closure_audit_package_blocks_linkage_mismatch():
    recovery, receipt, closure, closure_verification = _package_artifacts()
    tampered_closure = {**closure, "receipt_id": "other-receipt"}

    result = build_case_delivery_recovery_closure_audit_package(
        recovery,
        receipt,
        tampered_closure,
        closure_verification,
        package_owner="auditor",
    )

    assert result["status"] == "blocked"
    assert any(
        blocker["key"] == "closure_receipt_mismatch" for blocker in result["blockers"]
    )


def test_case_delivery_recovery_closure_audit_package_route_requires_login(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_case_delivery_workspace_routes_v15(app)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["_csrf_token"] = "test-csrf"

    response = client.post(
        "/api/v1/case-delivery/case-1/recovery-closure-audit-package",
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert response.status_code == 401


def test_case_delivery_recovery_closure_audit_package_route_returns_package(
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

    recovery, receipt, closure, closure_verification = _package_artifacts()
    response = client.post(
        "/api/v1/case-delivery/case-1/recovery-closure-audit-package",
        json={
            "recovery": recovery,
            "receipt": receipt,
            "closure": closure,
            "closure_verification": closure_verification,
            "package_owner": "auditor",
        },
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "packaged"
    assert payload["packaged"] is True
    assert payload["audit_package"]["audit_package_id"]


def test_v16_8_release_note_and_changelog_are_present():
    note = Path("release/V16_8_DELIVERY_RECOVERY_CLOSURE_AUDIT_PACKAGE.md").read_text(
        encoding="utf-8"
    )
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert "/api/v1/case-delivery/<case_id>/recovery-closure-audit-package" in note
    assert "v16.8 Delivery Recovery Closure Audit Package" in changelog
