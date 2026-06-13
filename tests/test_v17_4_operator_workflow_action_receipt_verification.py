from __future__ import annotations

from pathlib import Path

from src.socmint.case_delivery_operations_v16_0 import build_case_delivery_operations
from src.socmint.case_delivery_workspace_routes_v15 import register_case_delivery_workspace_routes_v15
from src.socmint.dashboard import create_app
from src.socmint.operator_release_console_routes_v14 import register_operator_release_console_routes_v14
from src.socmint.operator_workflow_action_launcher_v17_2 import launch_operator_workflow_action
from src.socmint.operator_workflow_action_receipt_v17_3 import build_operator_workflow_action_receipt
from src.socmint.operator_workflow_action_receipt_verification_v17_4 import (
    OPERATOR_WORKFLOW_ACTION_RECEIPT_VERIFICATION_SCHEMA,
    verify_operator_workflow_action_receipt,
)
from src.socmint.unified_operator_workflow_dashboard_routes_v17_1 import register_unified_operator_workflow_dashboard_routes_v17_1
from tests.test_v15_case_delivery_workspace import ready_payload


FIXED_TIME = "2026-06-12T22:00:00+00:00"


def _app():
    app = create_app()
    register_operator_release_console_routes_v14(app)
    register_case_delivery_workspace_routes_v15(app)
    register_unified_operator_workflow_dashboard_routes_v17_1(app)
    return app


def _ready_payload(case_id="case-v17-4"):
    payload = ready_payload(operator="operator", issuer="release-lead", authorizer="delivery-lead")
    payload["operations"] = build_case_delivery_operations(case_id, payload)
    return payload


def _action_and_receipt(action="open_case_delivery"):
    app = _app()
    result = launch_operator_workflow_action(
        "case-v17-4",
        {"action": action, "dashboard_payload": _ready_payload()},
        routes=list(app.url_map.iter_rules()),
    )
    receipt = build_operator_workflow_action_receipt(
        "case-v17-4",
        result,
        operator="operator",
        recorded_at=FIXED_TIME,
    )
    return result, receipt


def test_v17_4_verifies_valid_action_receipt():
    action_result, receipt = _action_and_receipt()

    result = verify_operator_workflow_action_receipt(
        receipt,
        action_result,
        expected_operator="operator",
        expected_case_id="case-v17-4",
    )

    assert result["schema"] == OPERATOR_WORKFLOW_ACTION_RECEIPT_VERIFICATION_SCHEMA
    assert result["status"] == "verified"
    assert result["verified"] is True
    assert result["receipt_hash_valid"] is True
    assert result["receipt_id_valid"] is True
    assert result["timestamp_valid"] is True
    assert result["operator_consistent"] is True
    assert result["action_result_consistent"] is True
    assert result["action_target_valid"] is True
    assert result["blocker_count"] == 0


def test_v17_4_blocks_tampered_hash_and_receipt_id():
    action_result, receipt = _action_and_receipt()
    tampered = {**receipt, "receipt_sha256": "tampered"}

    result = verify_operator_workflow_action_receipt(
        tampered,
        action_result,
        expected_operator="operator",
        expected_case_id="case-v17-4",
    )

    assert result["status"] == "blocked"
    assert any(item["key"] == "receipt_hash_mismatch" for item in result["blockers"])
    assert any(item["key"] == "action_receipt_id_mismatch" for item in result["blockers"])


def test_v17_4_blocks_invalid_timestamp_and_operator_mismatch():
    action_result, receipt = _action_and_receipt()
    tampered = {**receipt, "recorded_at": "not-a-timestamp"}

    result = verify_operator_workflow_action_receipt(
        tampered,
        action_result,
        expected_operator="different-operator",
        expected_case_id="case-v17-4",
    )

    assert result["status"] == "blocked"
    assert any(item["key"] == "invalid_recorded_at" for item in result["blockers"])
    assert any(item["key"] == "operator_mismatch" for item in result["blockers"])


def test_v17_4_blocks_action_result_and_target_mismatch():
    action_result, receipt = _action_and_receipt()
    tampered_result = {
        **action_result,
        "action": "open_release_console",
        "status": "blocked",
        "action_plan": {"type": "navigation", "target": "/operator/release-console"},
    }

    result = verify_operator_workflow_action_receipt(
        receipt,
        tampered_result,
        expected_operator="operator",
        expected_case_id="case-v17-4",
    )

    assert result["status"] == "blocked"
    assert any(item["key"] == "action_mismatch" for item in result["blockers"])
    assert any(item["key"] == "result_status_mismatch" for item in result["blockers"])
    assert any(item["key"] == "action_target_mismatch" for item in result["blockers"])


def test_v17_4_action_route_attaches_verified_receipt(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    client = _app().test_client()
    with client.session_transaction() as sess:
        sess["user"] = "operator"
        sess["_csrf_token"] = "test-csrf"

    response = client.post(
        "/api/v1/operator/workflow-dashboard/case-v17-4/actions",
        json={
            "action": "open_case_delivery",
            "recorded_at": FIXED_TIME,
            "dashboard_payload": _ready_payload(),
        },
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    verification = payload["action_receipt_verification"]
    assert verification["status"] == "verified"
    assert verification["verified"] is True
    assert verification["action_receipt_id"] == payload["action_receipt"]["action_receipt_id"]


def test_v17_4_dedicated_verify_route_accepts_valid_receipt(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    client = _app().test_client()
    with client.session_transaction() as sess:
        sess["user"] = "operator"
        sess["_csrf_token"] = "test-csrf"
    action_result, receipt = _action_and_receipt()

    response = client.post(
        "/api/v1/operator/workflow-dashboard/case-v17-4/actions/verify",
        json={"action_receipt": receipt, "action_result": action_result},
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert response.status_code == 200
    assert response.get_json()["status"] == "verified"


def test_v17_4_dedicated_verify_route_blocks_tampered_receipt(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    client = _app().test_client()
    with client.session_transaction() as sess:
        sess["user"] = "operator"
        sess["_csrf_token"] = "test-csrf"
    action_result, receipt = _action_and_receipt()
    receipt["action_target"] = "/wrong-target"

    response = client.post(
        "/api/v1/operator/workflow-dashboard/case-v17-4/actions/verify",
        json={"action_receipt": receipt, "action_result": action_result},
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert response.status_code == 409
    payload = response.get_json()
    assert payload["status"] == "blocked"
    assert any(item["key"] == "receipt_hash_mismatch" for item in payload["blockers"])
    assert any(item["key"] == "action_target_mismatch" for item in payload["blockers"])


def test_v17_4_release_note_and_changelog_are_present():
    note = Path("release/V17_4_OPERATOR_ACTION_RECEIPT_VERIFICATION.md").read_text(encoding="utf-8")
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert "/api/v1/operator/workflow-dashboard/<case_id>/actions/verify" in note
    assert "receipt_sha256" in note
    assert "v17.4 Operator Action Receipt Verification" in changelog
