from __future__ import annotations

from pathlib import Path

from src.socmint.case_delivery_workspace_routes_v15 import register_case_delivery_workspace_routes_v15
from src.socmint.dashboard import create_app
from src.socmint.operator_release_console_routes_v14 import register_operator_release_console_routes_v14
from src.socmint.unified_operator_workflow_dashboard_routes_v17_1 import (
    register_unified_operator_workflow_dashboard_routes_v17_1,
)


def _app():
    app = create_app()
    register_operator_release_console_routes_v14(app)
    register_case_delivery_workspace_routes_v15(app)
    register_unified_operator_workflow_dashboard_routes_v17_1(app)
    return app


def test_v17_6_dashboard_renders_feedback_loading_and_empty_states(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    client = _app().test_client()
    with client.session_transaction() as sess:
        sess["user"] = "operator"
        sess["_csrf_token"] = "test-csrf"

    response = client.get("/operator/workflow-dashboard?case_id=case-v17-6")

    assert response.status_code == 200
    assert b"operator-action-feedback" in response.data
    assert b"Loading action history" in response.data
    assert b"No operator actions have been recorded" in response.data
    assert b"Refresh history" in response.data


def test_v17_6_dashboard_disables_dispatch_when_not_ready(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    client = _app().test_client()
    with client.session_transaction() as sess:
        sess["user"] = "operator"

    response = client.get("/operator/workflow-dashboard?case_id=case-v17-6-blocked")

    assert response.status_code == 200
    assert b'data-action="dispatch_delivery_operations"' in response.data
    assert b'data-permanently-disabled="true"' in response.data
    assert b"Dispatch is disabled until all readiness checks pass" in response.data


def test_v17_6_dashboard_uses_client_side_action_controls(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    client = _app().test_client()
    with client.session_transaction() as sess:
        sess["user"] = "operator"

    response = client.get("/operator/workflow-dashboard?case_id=case-v17-6")

    assert response.status_code == 200
    assert b"data-workflow-action" in response.data
    assert b'data-requires-confirmation="true"' in response.data
    assert b"operator_workflow_dashboard_v17_6.js" in response.data


def test_v17_6_static_script_contains_feedback_and_history_refresh_logic():
    script = Path("src/socmint/static/operator_workflow_dashboard_v17_6.js").read_text(encoding="utf-8")

    assert "setBanner" in script
    assert "refreshHistory" in script
    assert "confirmation_required" in script
    assert "Operator action blocked" in script
    assert "X-CSRF-Token" in script
    assert "window.location.assign" in script
    assert "aria-busy" in script


def test_v17_6_static_script_is_served(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    client = _app().test_client()

    response = client.get("/static/operator_workflow_dashboard_v17_6.js")

    assert response.status_code == 200
    assert b"refreshHistory" in response.data
    assert response.mimetype in {"application/javascript", "text/javascript"}


def test_v17_6_release_note_and_changelog_are_present():
    note = Path("release/V17_6_OPERATOR_WORKFLOW_DASHBOARD_UX_HARDENING.md").read_text(encoding="utf-8")
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")
    template = Path("src/socmint/templates/unified_operator_workflow_dashboard.html").read_text(encoding="utf-8")

    assert "action-result feedback" in note
    assert "history refresh" in note
    assert "v17.6 Operator Workflow Dashboard UX Hardening" in changelog
    assert "Operator Guidance" in template
