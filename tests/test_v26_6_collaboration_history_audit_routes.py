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
        "schema": "socmint.collaboration_history_audit.v26_6",
        "version": "v26.6.0",
        "status": "attention_required",
        "generated_at": "2026-06-16T22:00:00+00:00",
        "user_identity": "paul",
        "access_scope": {"mode": "restricted", "allowed_case_ids": ["case-a"]},
        "history": [{
            "history_event_id": "e1", "event_type": "team_assignment",
            "occurred_at": "2026-06-16T20:00:00+00:00", "actor": "supervisor",
            "affected_user": "paul", "case_id": "case-a", "previous_state": None,
            "new_state": "active", "source_action": "case_team_role_assignment", "source_record_id": 1,
        }],
        "event_count": 1,
        "event_type_counts": {"team_assignment": 1},
        "actor_counts": {"supervisor": 1},
        "case_count": 1,
        "source_bound_event_count": 1,
        "current_collaboration_state": {
            "active_team": [{"case_id": "case-a", "user_identity": "paul", "role": "case_owner"}],
            "current_owner": "paul", "open_requests": [], "pending_handoffs": [],
            "unacknowledged_items": [], "overdue_items": [], "unresolved_responses": [],
            "active_escalations": [], "unresolved_actions": {"requests": 0},
        },
        "current_collaboration_state_sha256": "a" * 64,
        "source_records_mutated": False,
        "collaboration_events_mutated": False,
        "queue_record_created": False,
        "history_record_created": False,
        "case_access_scope_changed": False,
        "next_action": "review_collaboration_history_and_audit",
    }


def test_v26_6_routes_require_login_scope_and_render(tmp_path, monkeypatch):
    from src.socmint import collaboration_history_audit_routes_v26_6 as routes

    captured = []
    def build(user_identity, **kwargs):
        captured.append((user_identity, kwargs))
        return _payload()
    monkeypatch.setattr(routes, "build_collaboration_history_audit", build)
    client = _app(tmp_path, monkeypatch).test_client()

    assert client.get("/api/v1/collaboration/history").status_code == 401
    assert client.get("/collaboration/history").status_code in {302, 303}

    with client.session_transaction() as sess:
        sess["user"] = "paul"
        sess["allowed_case_ids"] = ["case-a"]

    ui = client.get("/collaboration/history")
    api = client.get("/api/v1/collaboration/history")
    assert ui.status_code == 200
    for phrase in (
        b"Collaboration History and Audit", b"Current Collaboration State",
        b"Event Counts", b"Actor Counts", b"Ordered History", b"State SHA-256",
        b"Team Workload Queue",
    ):
        assert phrase in ui.data
    assert api.status_code == 200
    assert api.get_json()["event_type_counts"]["team_assignment"] == 1
    assert captured == [
        ("paul", {"allowed_case_ids": {"case-a"}}),
        ("paul", {"allowed_case_ids": {"case-a"}}),
    ]


def test_v26_6_release_note_and_no_migration():
    note = Path("release/V26_6_COLLABORATION_HISTORY_AUDIT.md").read_text(encoding="utf-8")
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v26_6*")
    ]
    for phrase in (
        "team assignments and revocations", "notes and corrections", "mentions",
        "review requests", "task handoffs", "responses", "escalations", "resolutions",
        "actor", "affected user", "source binding", "access scope",
        "previous state", "new state", "current collaboration state", "read-only",
    ):
        assert phrase in note
    assert migrations == []
