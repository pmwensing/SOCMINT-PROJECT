from pathlib import Path

from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import (
    register_dossier_assembly_routes_v21_0,
)


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    monkeypatch.setenv(
        "SOCMINT_SECRET_KEY", "v28-0-route-test-secret-key-with-more-than-32-characters"
    )
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def test_v28_0_routes_require_login_and_render(tmp_path, monkeypatch):
    from src.socmint import administration_workspace_routes_v28_0 as routes

    payload = {
        "schema": "socmint.administration_workspace.v28_0",
        "version": "v28.0.0",
        "status": "ready",
        "user_summary": {"total": 1},
        "role_summary": {"role_counts": {"admin": 1}},
        "team_summary": {"event_count": 0},
        "active_sessions": [],
        "active_session_count": 0,
        "access_grant_summary": {"event_count": 0},
        "policy_summary": {"event_count": 0},
        "connector_summary": {"connector_count": 0},
        "system_health": {"overall_status": "healthy"},
        "pending_admin_actions": [],
        "pending_admin_action_count": 0,
        "recent_governance_events": [],
        "governance_event_count": 0,
        "access_scope": {
            "mode": "administrative_read_only",
            "secrets_visible": False,
            "mutations_allowed": False,
        },
        "workspace_sha256": "a" * 64,
        "read_only": True,
        "source_records_mutated": False,
        "user_records_mutated": False,
        "permission_records_mutated": False,
        "connector_records_mutated": False,
        "case_access_scope_changed": False,
    }
    monkeypatch.setattr(routes, "build_administration_workspace", lambda: payload)
    client = _app(tmp_path, monkeypatch).test_client()
    assert client.get("/api/v1/administration").status_code == 401
    assert client.get("/administration").status_code in {302, 303}
    with client.session_transaction() as sess:
        sess["user"] = "admin"
    ui = client.get("/administration")
    api = client.get("/api/v1/administration")
    assert ui.status_code == 200
    for phrase in (
        b"Administration Workspace",
        b"User and Role Summary",
        b"Active Sessions",
        b"Connectors and Platform Health",
    ):
        assert phrase in ui.data
    assert api.status_code == 200
    assert api.get_json()["status"] == "ready"


def test_v28_0_release_note_and_no_migration():
    note = Path("release/V28_0_ADMINISTRATION_WORKSPACE.md").read_text(encoding="utf-8")
    for phrase in (
        "Administration Workspace",
        "read-only aggregation layer",
        "user_summary",
        "role_summary",
        "team_summary",
        "active_sessions",
        "access_grant_summary",
        "policy_summary",
        "connector_summary",
        "system_health",
        "pending_admin_actions",
        "recent_governance_events",
        "no secret values",
        "no migration",
    ):
        assert phrase in note
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v28_0*")
    ]
    assert migrations == []
