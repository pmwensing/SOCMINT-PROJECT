from __future__ import annotations

from pathlib import Path

from src.socmint.case_delivery_recovery_execution_v16_4 import CASE_DELIVERY_RECOVERY_EXECUTION_SCHEMA
from src.socmint.case_delivery_recovery_execution_v16_4 import build_case_delivery_recovery_execution
from src.socmint.case_delivery_workspace_routes_v15 import register_case_delivery_workspace_routes_v15
from src.socmint.dashboard import create_app
from tests.test_v15_case_delivery_workspace import ready_payload


def retry_payload(**overrides) -> dict:
    payload = ready_payload(
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
    )
    payload.update(overrides)
    return payload


def test_case_delivery_recovery_execution_is_clear_without_recovery_items():
    result = build_case_delivery_recovery_execution(
        "case-v16-execution-clear",
        ready_payload(operator="operator", issuer="release-lead", authorizer="delivery-lead"),
    )

    assert result["schema"] == CASE_DELIVERY_RECOVERY_EXECUTION_SCHEMA
    assert result["state"] == "clear"
    assert result["execution_count"] == 0
    assert result["execution_record_id"]
    assert result["next_action"] == "continue_delivery"


def test_case_delivery_recovery_execution_records_default_retry_action():
    result = build_case_delivery_recovery_execution("case-v16-execution-retry", retry_payload())

    assert result["state"] == "completed"
    assert result["execution_count"] == 1
    assert result["retried_count"] == 1
    assert result["executions"][0]["execution_state"] == "retried"
    assert result["executions"][0]["successful"] is True
    assert result["executions"][0]["execution_id"]
    assert result["result_summary"]["next_action"] == "continue_delivery_after_recovery"


def test_case_delivery_recovery_execution_accepts_explicit_failed_state():
    recovery_result = build_case_delivery_recovery_execution("case-v16-execution-prep", retry_payload())
    recovery_id = recovery_result["executions"][0]["recovery_id"]

    result = build_case_delivery_recovery_execution(
        "case-v16-execution-failed",
        retry_payload(
            executions=[
                {
                    "recovery_id": recovery_id,
                    "state": "failed",
                    "operator": "operator",
                    "detail": "Retry failed; recipient still unavailable.",
                }
            ]
        ),
    )

    assert result["state"] == "failed"
    assert result["failed_count"] == 1
    assert result["executions"][0]["execution_state"] == "failed"
    assert result["executions"][0]["successful"] is False
    assert result["next_action"] == "review_failed_recovery_execution"


def test_case_delivery_recovery_execution_records_escalation_action():
    result = build_case_delivery_recovery_execution(
        "case-v16-execution-escalated",
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

    assert result["state"] == "completed"
    assert result["escalated_count"] == 1
    assert result["executions"][0]["execution_state"] == "escalated"


def test_case_delivery_recovery_execution_blocks_when_recovery_blocks():
    result = build_case_delivery_recovery_execution(
        "case-v16-execution-blocked",
        ready_payload(
            operator="operator",
            issuer="release-lead",
            authorizer="delivery-lead",
            events=[{"type": "exception", "operator": "delivery-lead", "detail": "Channel outage."}],
        ),
    )

    assert result["state"] == "blocked"
    assert any(blocker["key"] == "recovery_queue_blocked" for blocker in result["blockers"])
    assert result["next_action"] == "resolve_execution_blockers"


def test_case_delivery_recovery_execution_route_requires_login(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_case_delivery_workspace_routes_v15(app)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["_csrf_token"] = "test-csrf"

    response = client.post(
        "/api/v1/case-delivery/case-1/recovery-execution",
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert response.status_code == 401


def test_case_delivery_recovery_execution_route_returns_record_for_logged_in_user(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_case_delivery_workspace_routes_v15(app)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user"] = "operator"
        sess["is_admin"] = False
        sess["_csrf_token"] = "test-csrf"

    response = client.post(
        "/api/v1/case-delivery/case-1/recovery-execution",
        json=retry_payload(),
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["schema"] == CASE_DELIVERY_RECOVERY_EXECUTION_SCHEMA
    assert payload["state"] == "completed"
    assert payload["execution_record_id"]
    assert payload["executions"][0]["execution_id"]


def test_v16_4_release_note_and_changelog_are_present():
    note = Path("release/V16_4_DELIVERY_RECOVERY_EXECUTION_RECORD.md").read_text(encoding="utf-8")
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")
    template = Path("src/socmint/templates/case_delivery_workspace.html").read_text(encoding="utf-8")

    assert "/api/v1/case-delivery/<case_id>/recovery-execution" in note
    assert "v16.4 Delivery Recovery Execution Record" in changelog
    assert "/api/v1/case-delivery/{{ payload.case_id }}/recovery-execution" in template
