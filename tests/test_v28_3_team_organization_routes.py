from pathlib import Path

from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import (
    register_dossier_assembly_routes_v21_0,
)


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    monkeypatch.setenv(
        "SOCMINT_SECRET_KEY", "v28-3-route-test-secret-key-with-more-than-32-characters"
    )
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def test_v28_3_routes_require_admin_and_dispatch(tmp_path, monkeypatch):
    from src.socmint import team_organization_routes_v28_3 as routes

    payload = {
        "schema": "socmint.team_organizational_structure.v28_3",
        "version": "v28.3.0",
        "status": "ready",
        "teams": [],
        "active_teams": [],
        "team_count": 0,
        "active_team_count": 0,
        "member_assignment_count": 0,
        "supervised_team_count": 0,
        "organizational_scope_counts": {},
        "workload_group_counts": {},
        "organization_findings": [],
        "organization_finding_count": 0,
        "team_history": [],
        "team_event_count": 0,
        "team_membership_grants_case_access": False,
    }
    monkeypatch.setattr(
        routes, "actor_is_administrator", lambda actor: actor == "admin"
    )
    monkeypatch.setattr(routes, "build_team_organization_workspace", lambda: payload)
    monkeypatch.setattr(
        routes,
        "create_team",
        lambda **kwargs: {"status": "team_created", "team_id": "team-1"},
    )
    monkeypatch.setattr(
        routes,
        "revise_team",
        lambda *args, **kwargs: {"status": "team_revised", "team_id": "team-2"},
    )
    monkeypatch.setattr(
        routes,
        "append_team_event",
        lambda *args, **kwargs: {"status": "team_updated", "team_id": args[0]},
    )
    client = _app(tmp_path, monkeypatch).test_client()
    assert client.get("/api/v1/administration/teams").status_code == 401
    with client.session_transaction() as sess:
        sess["user"] = "viewer"
    assert client.get("/api/v1/administration/teams").status_code == 403
    csrf = "v28-3-csrf-token"
    with client.session_transaction() as sess:
        sess["user"] = "admin"
        sess["_csrf_token"] = csrf
    headers = {"X-CSRF-Token": csrf}
    assert client.get("/administration/teams").status_code == 200
    assert (
        client.post(
            "/api/v1/administration/teams",
            json={"name": "Alpha", "reason": "create", "confirmed": True},
            headers=headers,
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/administration/teams/team-1/revise",
            json={"name": "Beta", "reason": "revise", "confirmed": True},
            headers=headers,
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/administration/teams/team-1/members/add",
            json={"username": "alice", "reason": "add", "confirmed": True},
            headers=headers,
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/administration/teams/team-1/supervisor",
            json={"supervisor_username": "bob", "reason": "lead", "confirmed": True},
            headers=headers,
        ).status_code
        == 200
    )


def test_v28_3_release_note_and_no_migration():
    note = Path("release/V28_3_TEAM_ORGANIZATIONAL_STRUCTURE.md").read_text(
        encoding="utf-8"
    )
    for phrase in (
        "Team and Organizational Structure",
        "organizational scopes",
        "ownership boundaries",
        "workload groups",
        "immutable team history",
        "administrator required",
        "explicit confirmation",
        "administrative reason",
        "team membership does not grant case access",
        "no migration",
    ):
        assert phrase in note
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v28_3*")
    ]
    assert migrations == []
