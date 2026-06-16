from pathlib import Path

from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import register_dossier_assembly_routes_v21_0


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def _payload():
    return {
        "schema": "socmint.team_workload_collaboration_queue.v26_5",
        "version": "v26.5.0",
        "status": "attention_required",
        "generated_at": "2026-06-16T20:00:00+00:00",
        "access_scope": {"mode": "restricted", "allowed_case_ids": ["case-a"]},
        "user_identity": "paul",
        "my_assigned_cases": [{"case_id": "case-a", "assigned_roles": ["reviewer"]}],
        "pending_requests": [{"case_id": "case-a", "collaboration_request_id": "r1"}],
        "awaiting_acknowledgement": [{"case_id": "case-a", "collaboration_request_id": "r1"}],
        "delegated_by_me": [{"case_id": "case-a", "collaboration_request_id": "r1"}],
        "pending_handoffs": [],
        "overdue_items": [{"case_id": "case-a", "overdue_hours": 2.0}],
        "unassigned_work": [{"case_id": "case-a"}],
        "supervisor_escalations": [{"case_id": "case-a", "response_type": "escalation"}],
        "recent_activity": [{"case_id": "case-a", "action": "case_collaboration_note_created"}],
        "collaboration_load_by_user": [{
            "user_identity": "paul",
            "active_case_count": 1,
            "case_ids": ["case-a"],
            "roles": ["reviewer"],
            "open_requests": 0,
            "open_handoffs": 0,
            "unread_updates": 1,
            "total_collaboration_load": 2,
        }],
        "workload_imbalance": [],
        "counts": {
            "my_assigned_cases": 1,
            "pending_requests": 1,
            "awaiting_acknowledgement": 1,
            "delegated_by_me": 1,
            "pending_handoffs": 0,
            "overdue_items": 1,
            "unassigned_work": 1,
            "supervisor_escalations": 1,
            "recent_activity": 1,
            "users_with_load": 1,
            "workload_imbalance": 0,
        },
        "average_collaboration_load": 2.0,
        "queue_sha256": "q" * 64,
        "read_only": True,
        "source_records_mutated": False,
        "collaboration_record_created": False,
        "case_access_scope_changed": False,
        "next_action": "review_team_workload_and_collaboration_queue",
    }


def test_v26_5_routes_require_login_scope_and_render(tmp_path, monkeypatch):
    from src.socmint import team_workload_collaboration_queue_routes_v26_5 as routes

    captured = []

    def build(user_identity, **kwargs):
        captured.append((user_identity, kwargs))
        return _payload()

    monkeypatch.setattr(routes, "build_team_workload_collaboration_queue", build)
    client = _app(tmp_path, monkeypatch).test_client()

    assert client.get("/api/v1/collaboration/my-work").status_code == 401
    assert client.get("/collaboration/my-work").status_code in {302, 303}

    with client.session_transaction() as sess:
        sess["user"] = "paul"
        sess["allowed_case_ids"] = ["case-a"]

    ui = client.get("/collaboration/my-work")
    api = client.get("/api/v1/collaboration/my-work")

    assert ui.status_code == 200
    for phrase in (
        b"Team Workload and Collaboration Queue",
        b"My Assigned Cases",
        b"Pending Requests",
        b"Awaiting Acknowledgement",
        b"Delegated by Me",
        b"Overdue Collaboration Items",
        b"Unassigned Collaboration Work",
        b"Supervisor Escalation Queue",
        b"Collaboration Load by User",
        b"Recent Team Activity",
        b"Reviewer Queue",
        b"Supervisor Queue",
        b"v26.5 is read-only",
    ):
        assert phrase in ui.data
    assert api.status_code == 200
    assert api.get_json()["counts"]["overdue_items"] == 1
    assert all(user == "paul" for user, _ in captured)
    assert all(kwargs["allowed_case_ids"] == {"case-a"} for _, kwargs in captured)


def test_v26_5_release_note_and_no_migration():
    note = Path("release/V26_5_TEAM_WORKLOAD_COLLABORATION_QUEUE.md").read_text(encoding="utf-8")
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v26_5*")
    ]
    for phrase in (
        "my assigned cases",
        "pending requests",
        "awaiting acknowledgement",
        "delegated work",
        "overdue collaboration items",
        "unassigned collaboration work",
        "supervisor escalation queue",
        "recent team activity",
        "collaboration load by user",
        "workload imbalance",
        "reviewer queue",
        "supervisor queue",
        "read-only",
    ):
        assert phrase in note
    assert migrations == []
