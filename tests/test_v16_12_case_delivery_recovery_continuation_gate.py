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
from src.socmint.case_delivery_recovery_continuation_gate_v16_12 import (
    CASE_DELIVERY_RECOVERY_CONTINUATION_GATE_SCHEMA,
)
from src.socmint.case_delivery_recovery_continuation_gate_v16_12 import (
    build_case_delivery_recovery_continuation_gate,
)
from src.socmint.case_delivery_recovery_finalization_record_v16_10 import (
    build_case_delivery_recovery_finalization_record,
)
from src.socmint.case_delivery_recovery_finalization_record_verification_v16_11 import (
    verify_case_delivery_recovery_finalization_record,
)
from src.socmint.case_delivery_recovery_v16_3 import build_case_delivery_recovery
from src.socmint.case_delivery_workspace_routes_v15 import (
    register_case_delivery_workspace_routes_v15,
)
from src.socmint.dashboard import create_app
from tests.test_v15_case_delivery_workspace import ready_payload


def _gate_artifacts():
    recovery = build_case_delivery_recovery(
        "case-v16-12-gate",
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
        "case-v16-12-gate",
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
    return (
        recovery,
        receipt,
        closure,
        audit_package,
        audit_verification,
        finalization,
        finalization_verification,
    )


def test_case_delivery_recovery_continuation_gate_opens_after_verified_finalization():
    (
        recovery,
        receipt,
        closure,
        audit_package,
        audit_verification,
        finalization,
        finalization_verification,
    ) = _gate_artifacts()

    result = build_case_delivery_recovery_continuation_gate(
        recovery,
        receipt,
        closure,
        audit_package,
        audit_verification,
        finalization,
        finalization_verification,
        gate_operator="delivery-ops",
    )

    assert result["status"] == "open"
    assert result["gate_open"] is True
    assert result["ready_for_delivery_continuation"] is True
    assert result["next_action"] == "resume_delivery_operations"
    gate = result["continuation_gate"]
    assert gate["schema"] == CASE_DELIVERY_RECOVERY_CONTINUATION_GATE_SCHEMA
    assert gate["gate_operator"] == "delivery-ops"
    assert gate["gate_open"] is True
    assert gate["continuation_gate_id"]
    assert gate["finalization_id"] == finalization["finalization_id"]
    assert result["blocker_count"] == 0


def test_case_delivery_recovery_continuation_gate_id_is_deterministic_and_operator_sensitive():
    (
        recovery,
        receipt,
        closure,
        audit_package,
        audit_verification,
        finalization,
        finalization_verification,
    ) = _gate_artifacts()

    first = build_case_delivery_recovery_continuation_gate(
        recovery,
        receipt,
        closure,
        audit_package,
        audit_verification,
        finalization,
        finalization_verification,
        gate_operator="delivery-ops",
    )
    second = build_case_delivery_recovery_continuation_gate(
        recovery,
        receipt,
        closure,
        audit_package,
        audit_verification,
        finalization,
        finalization_verification,
        gate_operator="delivery-ops",
    )
    changed = build_case_delivery_recovery_continuation_gate(
        recovery,
        receipt,
        closure,
        audit_package,
        audit_verification,
        finalization,
        finalization_verification,
        gate_operator="other-ops",
    )

    assert (
        first["continuation_gate"]["continuation_gate_id"]
        == second["continuation_gate"]["continuation_gate_id"]
    )
    assert (
        first["continuation_gate"]["continuation_gate_id"]
        != changed["continuation_gate"]["continuation_gate_id"]
    )


def test_case_delivery_recovery_continuation_gate_blocks_failed_finalization_verification():
    (
        recovery,
        receipt,
        closure,
        audit_package,
        audit_verification,
        finalization,
        _finalization_verification,
    ) = _gate_artifacts()
    failed_verification = {
        "status": "blocked",
        "verified": False,
        "ready_for_delivery_continuation": False,
        "blockers": [{"key": "tampered", "detail": "tampered"}],
    }

    result = build_case_delivery_recovery_continuation_gate(
        recovery,
        receipt,
        closure,
        audit_package,
        audit_verification,
        finalization,
        failed_verification,
        gate_operator="delivery-ops",
    )

    assert result["status"] == "blocked"
    assert result["gate_open"] is False
    assert result["ready_for_delivery_continuation"] is False
    assert result["continuation_gate"] is None
    assert result["next_action"] == "resolve_recovery_finalization"
    assert any(
        blocker["key"] == "finalization_verification_blocked"
        for blocker in result["blockers"]
    )


def test_case_delivery_recovery_continuation_gate_blocks_linkage_mismatch():
    (
        recovery,
        receipt,
        closure,
        audit_package,
        audit_verification,
        finalization,
        finalization_verification,
    ) = _gate_artifacts()
    tampered_finalization = {**finalization, "finalization_id": "other-finalization"}

    result = build_case_delivery_recovery_continuation_gate(
        recovery,
        receipt,
        closure,
        audit_package,
        audit_verification,
        tampered_finalization,
        finalization_verification,
        gate_operator="delivery-ops",
    )

    assert result["status"] == "blocked"
    assert any(
        blocker["key"] == "finalization_id_mismatch" for blocker in result["blockers"]
    )


def test_case_delivery_recovery_continuation_gate_route_requires_login(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_case_delivery_workspace_routes_v15(app)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["_csrf_token"] = "test-csrf"

    response = client.post(
        "/api/v1/case-delivery/case-1/recovery-continuation-gate",
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert response.status_code == 401


def test_case_delivery_recovery_continuation_gate_route_returns_open(
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

    (
        recovery,
        receipt,
        closure,
        audit_package,
        audit_verification,
        finalization,
        finalization_verification,
    ) = _gate_artifacts()
    response = client.post(
        "/api/v1/case-delivery/case-1/recovery-continuation-gate",
        json={
            "recovery": recovery,
            "receipt": receipt,
            "closure": closure,
            "audit_package": audit_package,
            "audit_verification": audit_verification,
            "finalization": finalization,
            "finalization_verification": finalization_verification,
            "gate_operator": "delivery-ops",
        },
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "open"
    assert payload["gate_open"] is True
    assert payload["ready_for_delivery_continuation"] is True
    assert payload["next_action"] == "resume_delivery_operations"
    assert payload["continuation_gate"]["continuation_gate_id"]


def test_v16_12_release_note_and_changelog_are_present():
    note = Path("release/V16_12_DELIVERY_RECOVERY_CONTINUATION_GATE.md").read_text(
        encoding="utf-8"
    )
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert "/api/v1/case-delivery/<case_id>/recovery-continuation-gate" in note
    assert "v16.12 Delivery Recovery Continuation Gate" in changelog
