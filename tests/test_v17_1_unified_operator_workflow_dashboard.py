from __future__ import annotations

from pathlib import Path

from src.socmint.case_delivery_operations_v16_0 import build_case_delivery_operations
from src.socmint.case_delivery_workspace_routes_v15 import register_case_delivery_workspace_routes_v15
from src.socmint.dashboard import create_app
from src.socmint.operator_release_console_routes_v14 import register_operator_release_console_routes_v14
from src.socmint.unified_operator_workflow_dashboard_routes_v17_1 import (
    register_unified_operator_workflow_dashboard_routes_v17_1,
)
from src.socmint.unified_operator_workflow_dashboard_v17_1 import (
    UNIFIED_OPERATOR_WORKFLOW_DASHBOARD_SCHEMA,
    build_unified_operator_workflow_dashboard,
)
from tests.test_v15_case_delivery_workspace import ready_payload


def _app_with_operator_routes():
    app = create_app()
    register_operator_release_console_routes_v14(app)
    register_case_delivery_workspace_routes_v15(app)
    register_unified_operator_workflow_dashboard_routes_v17_1(app)
    return app


def _ready_dashboard_payload():
    payload = ready_payload(
        operator="operator",
        issuer="release-lead",
        authorizer="delivery-lead",
    )
    payload["operations"] = build_case_delivery_operations("case-v17-1-ready", payload)
    return payload


def test_v17_1_dashboard_combines_operator_workflow_state():
    app = _app_with_operator_routes()
    payload = _ready_dashboard_payload()

    result = build_unified_operator_workflow_dashboard(
        "case-v17-1-ready",
        payload,
        routes=list(app.url_map.iter_rules()),
    )

    assert result["schema"] == UNIFIED_OPERATOR_WORKFLOW_DASHBOARD_SCHEMA
    assert result["case_id"] == "case-v17-1-ready"
    assert result["status"] == "ready"
    assert result["summary"]["case_delivery_ready"] is True
    assert result["summary"]["recovery_chain_closed"] is True
    assert result["summary"]["operations_dispatchable"] is True
    assert result["case_delivery"]["decision"] == "READY_FOR_DELIVERY"
    assert result["recovery_chain"]["status"] == "closed"
    assert result["operations"]["dispatchable"] is True
    assert result["release_console"]["release_health"]
    assert result["recommended_action"]["source"] in {"operations", "release_console"}


def test_v17_1_dashboard_prioritizes_case_delivery_blockers():
    app = _app_with_operator_routes()
    payload = ready_payload(
        approval_decision="pending_review",
        operations={"state": "ready_for_dispatch", "dispatchable": True, "blockers": [], "next_action": "dispatch_delivery"},
    )

    result = build_unified_operator_workflow_dashboard(
        "case-v17-1-blocked",
        payload,
        routes=list(app.url_map.iter_rules()),
    )

    assert result["status"] == "attention_required"
    assert result["recommended_action"]["source"] == "case_delivery"
    assert result["recommended_action"]["key"] == "approve_delivery"
    assert any(blocker["source"] == "case_delivery" for blocker in result["blockers"])


def test_v17_1_dashboard_routes_require_login(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = _app_with_operator_routes()
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["_csrf_token"] = "test-csrf"

    ui_response = client.get("/operator/workflow-dashboard?case_id=case-1")
    api_response = client.get("/api/v1/operator/workflow-dashboard/case-1")
    post_response = client.post(
        "/api/v1/operator/workflow-dashboard/case-1",
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert ui_response.status_code == 302
    assert api_response.status_code == 401
    assert post_response.status_code == 401


def test_v17_1_dashboard_api_returns_ready_payload(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = _app_with_operator_routes()
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user"] = "operator"
        sess["_csrf_token"] = "test-csrf"

    response = client.post(
        "/api/v1/operator/workflow-dashboard/case-v17-1-ready",
        json=_ready_dashboard_payload(),
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["schema"] == UNIFIED_OPERATOR_WORKFLOW_DASHBOARD_SCHEMA
    assert payload["status"] == "ready"
    assert payload["summary"]["recovery_chain_closed"] is True
    assert payload["recommended_action"]["key"] in {"dispatch_delivery_operations", "refresh_release_health"}


def test_v17_1_dashboard_ui_renders_for_logged_in_operator(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = _app_with_operator_routes()
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user"] = "operator"

    response = client.get("/operator/workflow-dashboard?case_id=case-v17-1-ui")

    assert response.status_code == 200
    assert b"Unified Operator Workflow Dashboard" in response.data
    assert b"Recommended Next Action" in response.data
    assert b"Active Blockers" in response.data


def test_v17_1_release_note_changelog_and_template_are_present():
    note = Path("release/V17_1_UNIFIED_OPERATOR_WORKFLOW_DASHBOARD.md").read_text(encoding="utf-8")
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")
    template = Path("src/socmint/templates/unified_operator_workflow_dashboard.html").read_text(encoding="utf-8")

    assert "/api/v1/operator/workflow-dashboard/<case_id>" in note
    assert "/operator/workflow-dashboard" in note
    assert "v17.1 Unified Operator Workflow Dashboard" in changelog
    assert "Recommended Next Action" in template
