from __future__ import annotations

from pathlib import Path

from src.socmint.case_delivery_operations_v16_0 import build_case_delivery_operations
from src.socmint.case_delivery_workspace_routes_v15 import register_case_delivery_workspace_routes_v15
from src.socmint.dashboard import create_app
from src.socmint.operator_action_session_timeline_v17_5 import (
    DEFAULT_MAX_ENTRIES,
    OPERATOR_ACTION_SESSION_TIMELINE_SCHEMA,
    append_operator_action_history,
    build_operator_action_session_timeline,
)
from src.socmint.operator_release_console_routes_v14 import register_operator_release_console_routes_v14
from src.socmint.unified_operator_workflow_dashboard_routes_v17_1 import (
    register_unified_operator_workflow_dashboard_routes_v17_1,
)
from tests.test_v15_case_delivery_workspace import ready_payload


def _app():
    app = create_app()
    register_operator_release_console_routes_v14(app)
    register_case_delivery_workspace_routes_v15(app)
    register_unified_operator_workflow_dashboard_routes_v17_1(app)
    return app


def _ready_payload(case_id="case-v17-5"):
    payload = ready_payload(operator="operator", issuer="release-lead", authorizer="delivery-lead")
    payload["operations"] = build_case_delivery_operations(case_id, payload)
    return payload


def _receipt(index: int, *, case_id="case-v17-5", operator="operator"):
    return {
        "action_receipt_id": f"receipt-{index}",
        "case_id": case_id,
        "operator": operator,
        "action": "open_case_delivery",
        "label": "Open case-delivery workspace",
        "confirmed": False,
        "state_change": False,
        "action_target": f"/case-delivery?case_id={case_id}",
        "result_status": "launched",
        "recorded_at": f"2026-06-12T22:{index:02d}:00+00:00",
    }


def _verification(status="verified"):
    return {
        "status": status,
        "verified": status == "verified",
        "blocker_count": 0 if status == "verified" else 1,
        "next_action": "accept_operator_action_receipt" if status == "verified" else "resolve_operator_action_receipt",
    }


def test_v17_5_builds_reverse_chronological_session_timeline():
    history = []
    history = append_operator_action_history(history, _receipt(1), _verification())
    history = append_operator_action_history(history, _receipt(2), _verification("blocked"))

    timeline = build_operator_action_session_timeline(history, case_id="case-v17-5", operator="operator")

    assert timeline["schema"] == OPERATOR_ACTION_SESSION_TIMELINE_SCHEMA
    assert timeline["entry_count"] == 2
    assert timeline["verified_count"] == 1
    assert timeline["blocked_count"] == 1
    assert timeline["entries"][0]["action_receipt_id"] == "receipt-2"
    assert timeline["persistence"] == "flask_session_only"


def test_v17_5_history_deduplicates_and_caps_entries():
    history = []
    for index in range(DEFAULT_MAX_ENTRIES + 5):
        history = append_operator_action_history(history, _receipt(index), _verification())
    history = append_operator_action_history(history, _receipt(DEFAULT_MAX_ENTRIES + 4), _verification("blocked"))

    assert len(history) == DEFAULT_MAX_ENTRIES
    assert history[-1]["action_receipt_id"] == f"receipt-{DEFAULT_MAX_ENTRIES + 4}"
    assert history[-1]["verification_status"] == "blocked"
    assert len({item["action_receipt_id"] for item in history}) == DEFAULT_MAX_ENTRIES


def test_v17_5_timeline_filters_case_and_operator():
    history = [
        append_operator_action_history([], _receipt(1), _verification())[0],
        append_operator_action_history([], _receipt(2, case_id="other-case"), _verification())[0],
        append_operator_action_history([], _receipt(3, operator="other-operator"), _verification())[0],
    ]

    timeline = build_operator_action_session_timeline(history, case_id="case-v17-5", operator="operator")

    assert timeline["entry_count"] == 1
    assert timeline["entries"][0]["action_receipt_id"] == "receipt-1"


def test_v17_5_action_route_records_session_history(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    client = _app().test_client()
    with client.session_transaction() as sess:
        sess["user"] = "operator"
        sess["_csrf_token"] = "test-csrf"

    response = client.post(
        "/api/v1/operator/workflow-dashboard/case-v17-5/actions",
        json={
            "action": "open_case_delivery",
            "recorded_at": "2026-06-12T22:30:00+00:00",
            "dashboard_payload": _ready_payload(),
        },
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["action_history"]["entry_count"] == 1
    assert payload["action_history"]["entries"][0]["verified"] is True


def test_v17_5_history_api_returns_current_case_timeline(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    client = _app().test_client()
    with client.session_transaction() as sess:
        sess["user"] = "operator"
        sess["_csrf_token"] = "test-csrf"

    client.post(
        "/api/v1/operator/workflow-dashboard/case-v17-5/actions",
        json={"action": "open_case_delivery", "dashboard_payload": _ready_payload()},
        headers={"X-CSRF-Token": "test-csrf"},
    )
    response = client.get("/api/v1/operator/workflow-dashboard/case-v17-5/actions/history")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["entry_count"] == 1
    assert payload["case_id"] == "case-v17-5"
    assert payload["operator"] == "operator"


def test_v17_5_dashboard_api_and_ui_include_session_timeline(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    client = _app().test_client()
    with client.session_transaction() as sess:
        sess["user"] = "operator"
        sess["_csrf_token"] = "test-csrf"

    client.post(
        "/api/v1/operator/workflow-dashboard/case-v17-5/actions",
        json={"action": "open_case_delivery", "dashboard_payload": _ready_payload()},
        headers={"X-CSRF-Token": "test-csrf"},
    )
    api_response = client.get("/api/v1/operator/workflow-dashboard/case-v17-5")
    ui_response = client.get("/operator/workflow-dashboard?case_id=case-v17-5")

    assert api_response.status_code == 200
    assert api_response.get_json()["action_history"]["entry_count"] == 1
    assert ui_response.status_code == 200
    assert b"Operator Action History" in ui_response.data
    assert b"Open case-delivery workspace" in ui_response.data


def test_v17_5_release_note_changelog_and_template_are_present():
    note = Path("release/V17_5_OPERATOR_ACTION_HISTORY_SESSION_TIMELINE.md").read_text(encoding="utf-8")
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")
    template = Path("src/socmint/templates/unified_operator_workflow_dashboard.html").read_text(encoding="utf-8")

    assert "/api/v1/operator/workflow-dashboard/<case_id>/actions/history" in note
    assert "v17.5 Operator Action History / Session Timeline" in changelog
    assert "Operator Action History" in template
