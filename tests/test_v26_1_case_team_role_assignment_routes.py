from pathlib import Path

from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import register_dossier_assembly_routes_v21_0


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def _workspace():
    return {
        "schema": "socmint.case_team_role_assignment.v26_1",
        "version": "v26.1.0",
        "status": "ready",
        "case_id": "case-a",
        "role_catalog": ["case_owner", "lead_analyst", "analyst", "reviewer", "supervisor", "evidence_custodian", "observer"],
        "current_assignments": [{
            "case_team_assignment_id": "assignment-1",
            "case_team_event_sha256": "a" * 64,
            "user_identity": "alice",
            "role": "reviewer",
            "assignment_status": "active",
            "effective_from": None,
            "effective_until": None,
        }],
        "active_assignments": [],
        "active_assignment_count": 1,
        "history": [{
            "recorded_at": "2026-06-16T14:00:00+00:00",
            "event_type": "assignment",
            "user_identity": "alice",
            "role": "reviewer",
            "recorded_by": "supervisor",
            "reason": "Review the case.",
            "source_case_state_sha256": "s" * 64,
        }],
        "history_count": 1,
        "source_records_mutated": False,
        "read_only_view_created_record": False,
        "case_access_scope_changed": False,
        "next_action": "manage_case_team_roles",
    }


def test_v26_1_routes_require_login_enforce_scope_and_render(tmp_path, monkeypatch):
    from src.socmint import case_team_role_assignment_routes_v26_1 as routes

    monkeypatch.setattr(routes, "build_case_team_workspace", lambda case_id: _workspace())
    monkeypatch.setattr(routes, "assign_case_team_role", lambda case_id, **kwargs: {
        "status": "case_team_assignment_recorded",
        "case_id": case_id,
        "case_team_assignment_id": "assignment-2",
        "recorded_by": kwargs["assigned_by"],
    })
    monkeypatch.setattr(routes, "revoke_case_team_role", lambda case_id, assignment_id, **kwargs: {
        "status": "case_team_revocation_recorded",
        "case_id": case_id,
        "case_team_assignment_id": assignment_id,
        "recorded_by": kwargs["revoked_by"],
    })

    client = _app(tmp_path, monkeypatch).test_client()
    assert client.get("/api/v1/cases/case-a/team").status_code == 401
    assert client.get("/cases/case-a/team").status_code in {302, 303}

    with client.session_transaction() as sess:
        sess["user"] = "supervisor"
        sess["allowed_case_ids"] = ["case-a"]
        sess["_csrf_token"] = "csrf-v26-1"

    assert client.get("/api/v1/cases/case-hidden/team").status_code == 403
    assert client.post(
        "/api/v1/cases/case-hidden/team/assignments",
        json={"confirmed": True},
        headers={"X-CSRF-Token": "csrf-v26-1"},
    ).status_code == 403

    ui = client.get("/cases/case-a/team")
    api = client.get("/api/v1/cases/case-a/team")
    assignment = client.post(
        "/api/v1/cases/case-a/team/assignments",
        json={"user_identity": "bob", "role": "analyst", "reason": "Assist.", "confirmed": True},
        headers={"X-CSRF-Token": "csrf-v26-1"},
    )
    revocation = client.post(
        "/api/v1/cases/case-a/team/assignments/assignment-1/revoke",
        json={"reason": "Complete.", "confirmed": True},
        headers={"X-CSRF-Token": "csrf-v26-1"},
    )

    assert ui.status_code == 200
    assert b"Case Team and Role Assignment" in ui.data
    assert b"Assign Team Role" in ui.data
    assert b"Current Assignments" in ui.data
    assert b"Assignment History" in ui.data
    assert b"automatically grant or remove underlying case access" in ui.data
    assert api.status_code == 200
    assert api.get_json()["active_assignment_count"] == 1
    assert assignment.status_code == 200
    assert assignment.get_json()["recorded_by"] == "supervisor"
    assert revocation.status_code == 200
    assert revocation.get_json()["case_team_assignment_id"] == "assignment-1"


def test_v26_1_release_note_client_and_no_migration():
    note = Path("release/V26_1_CASE_TEAM_ROLE_ASSIGNMENT.md").read_text(encoding="utf-8")
    client = Path("src/socmint/static/case_team_role_assignment_v26_1.js").read_text(encoding="utf-8")
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v26_1*")
    ]
    for phrase in (
        "case owner",
        "lead analyst",
        "evidence custodian",
        "append-only",
        "assignment ID and SHA-256",
        "source case state",
        "supersedes",
        "revocation",
        "does not grant case access",
        "no migration",
    ):
        assert phrase in note
    assert "record-case-team-assignment" in client
    assert "revoke-case-team-role" in client
    assert migrations == []
