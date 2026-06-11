from __future__ import annotations

from pathlib import Path

from src.socmint.case_delivery_recovery_v16_3 import CASE_DELIVERY_RECOVERY_SCHEMA
from src.socmint.case_delivery_recovery_v16_3 import build_case_delivery_recovery
from src.socmint.case_delivery_workspace_routes_v15 import register_case_delivery_workspace_routes_v15
from src.socmint.dashboard import create_app
from tests.test_v15_case_delivery_workspace import ready_payload


def test_case_delivery_recovery_is_clear_without_exceptions():
    result = build_case_delivery_recovery(
        "case-v16-recovery-clear",
        ready_payload(operator="operator", issuer="release-lead", authorizer="delivery-lead"),
    )

    assert result["schema"] == CASE_DELIVERY_RECOVERY_SCHEMA
    assert result["state"] == "clear"
    assert result["recovery_count"] == 0
    assert result["queue_id"]
    assert result["next_action"] == "continue_delivery"


def test_case_delivery_recovery_builds_retry_queue_item():
    result = build_case_delivery_recovery(
        "case-v16-recovery-retry",
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

    assert result["state"] == "retry_ready"
    assert result["retry_count"] == 1
    assert result["operator_recovery_queue"][0]["decision"] == "retry"
    assert result["operator_recovery_queue"][0]["queue_state"] == "ready_for_retry"
    assert result["operator_recovery_queue"][0]["recommendation"] == "retry_after_operator_confirmation"
    assert result["operator_recovery_queue"][0]["recovery_id"]
    assert result["next_action"] == "operator_retry_delivery"


def test_case_delivery_recovery_escalates_rejected_delivery():
    result = build_case_delivery_recovery(
        "case-v16-recovery-escalate",
        ready_payload(
            operator="operator",
            issuer="release-lead",
            authorizer="delivery-lead",
            attempts=[
                {
                    "channel": "secure_portal",
                    "status": "failed",
                    "operator": "delivery-lead",
                    "detail": "Recipient rejected delivery.",
                }
            ],
        ),
    )

    assert result["state"] == "escalation_required"
    assert result["escalate_count"] == 1
    assert result["operator_recovery_queue"][0]["decision"] == "escalate"
    assert result["operator_recovery_queue"][0]["recommendation"] == "escalate_to_delivery_owner"
    assert result["next_action"] == "escalate_delivery_exception"


def test_case_delivery_recovery_remediates_retryable_channel_failure():
    result = build_case_delivery_recovery(
        "case-v16-recovery-remediate",
        ready_payload(
            operator="operator",
            issuer="release-lead",
            authorizer="delivery-lead",
            attempts=[
                {
                    "channel": "unspecified",
                    "status": "failed",
                    "operator": "delivery-lead",
                    "detail": "Channel outage.",
                }
            ],
        ),
    )

    assert result["state"] == "remediation_required"
    assert result["remediate_count"] == 1
    assert result["operator_recovery_queue"][0]["decision"] == "remediate"
    assert result["operator_recovery_queue"][0]["recommendation"] == "remediate_channel_and_retry"


def test_case_delivery_recovery_blocks_when_exception_review_blocks():
    result = build_case_delivery_recovery(
        "case-v16-recovery-blocked",
        ready_payload(
            operator="operator",
            issuer="release-lead",
            authorizer="delivery-lead",
            events=[{"type": "exception", "operator": "delivery-lead", "detail": "Channel outage."}],
        ),
    )

    assert result["state"] == "blocked"
    assert any(blocker["key"] == "exception_review_blocked" for blocker in result["blockers"])
    assert result["next_action"] == "resolve_recovery_blockers"


def test_case_delivery_recovery_route_requires_login(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_case_delivery_workspace_routes_v15(app)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["_csrf_token"] = "test-csrf"

    response = client.post(
        "/api/v1/case-delivery/case-1/recovery",
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert response.status_code == 401


def test_case_delivery_recovery_route_returns_queue_for_logged_in_user(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_case_delivery_workspace_routes_v15(app)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user"] = "operator"
        sess["is_admin"] = False
        sess["_csrf_token"] = "test-csrf"

    response = client.post(
        "/api/v1/case-delivery/case-1/recovery",
        json=ready_payload(
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
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["schema"] == CASE_DELIVERY_RECOVERY_SCHEMA
    assert payload["state"] == "retry_ready"
    assert payload["queue_id"]
    assert payload["operator_recovery_queue"][0]["recovery_id"]


def test_v16_3_release_note_and_changelog_are_present():
    note = Path("release/V16_3_DELIVERY_RECOVERY_RETRY_RESOLUTION.md").read_text(encoding="utf-8")
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")
    template = Path("src/socmint/templates/case_delivery_workspace.html").read_text(encoding="utf-8")

    assert "/api/v1/case-delivery/<case_id>/recovery" in note
    assert "v16.3 Delivery Recovery / Retry Resolution Layer" in changelog
    assert "/api/v1/case-delivery/{{ payload.case_id }}/recovery" in template
