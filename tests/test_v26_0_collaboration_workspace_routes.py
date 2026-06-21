from pathlib import Path

from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import (
    register_dossier_assembly_routes_v21_0,
)


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def test_v26_0_routes_require_login_apply_scope_and_render(tmp_path, monkeypatch):
    from src.socmint import collaboration_routes_v26_0 as routes

    captured = []
    payload = {
        "schema": "socmint.collaboration_workspace.v26_0",
        "version": "v26.0.0",
        "status": "attention_required",
        "user_identity": "paul",
        "access_scope": {"mode": "restricted", "allowed_case_ids": ["case-a"]},
        "participating_cases": [
            {
                "case_id": "case-a",
                "assigned_roles": ["reviewer"],
                "participation_reasons": ["assigned_review_work"],
                "stage": "active",
                "status": "operational",
                "blocked": False,
                "blockers": [],
                "active_collaborators": ["alice"],
                "latest_activity_at": "2026-06-16T09:00:00+00:00",
                "links": {
                    "case": "/case-intelligence-review/case-a",
                    "evidence": "/dossier-assembly/case-a",
                    "review": "/case-intelligence-review/case-a",
                    "closure": "/case-closure/case-a",
                    "archive": "/case-closure/case-a/history",
                    "release": "/dossier-release/case-a",
                    "cross_case": "/cross-case-intelligence",
                    "relationship_graph": "/cross-case-intelligence/graph",
                },
            }
        ],
        "active_collaborators": [
            {"user_identity": "alice", "case_ids": ["case-a"], "shared_case_count": 1}
        ],
        "pending_requests": [
            {"collaboration_request_id": "request-1", "case_id": "case-a"}
        ],
        "pending_handoffs": [],
        "unread_updates": [
            {"collaboration_update_id": "mention-1", "case_id": "case-a"}
        ],
        "unresolved_review_requests": [],
        "blocked_collaboration_items": [],
        "unresolved_collaboration_actions": [
            {"key": "respond_to_collaboration_request", "case_id": "case-a"}
        ],
        "counts": {
            "participating_cases": 1,
            "active_collaborators": 1,
            "pending_requests": 1,
            "pending_handoffs": 0,
            "unread_updates": 1,
            "unresolved_review_requests": 0,
            "blocked_collaboration_items": 0,
            "unresolved_collaboration_actions": 1,
        },
        "workspace_sha256": "w" * 64,
        "read_only": True,
        "source_records_mutated": False,
        "collaboration_record_created": False,
        "access_granted_by_mention": False,
        "next_action": "review_collaboration_workspace",
    }

    def build(user_identity, **kwargs):
        captured.append((user_identity, kwargs))
        return payload

    monkeypatch.setattr(routes, "build_collaboration_workspace", build)
    client = _app(tmp_path, monkeypatch).test_client()

    assert client.get("/api/v1/collaboration").status_code == 401
    assert client.get("/collaboration").status_code in {302, 303}

    with client.session_transaction() as sess:
        sess["user"] = "paul"
        sess["allowed_case_ids"] = ["case-a"]

    ui = client.get("/collaboration")
    api = client.get("/api/v1/collaboration")

    assert ui.status_code == 200
    assert b"Collaboration Workspace" in ui.data
    assert b"Participating Cases" in ui.data
    assert b"Active Collaborators" in ui.data
    assert b"Pending Requests and Handoffs" in ui.data
    assert b"Unread Mentions or Updates" in ui.data
    assert b"Blocked Collaboration Items" in ui.data
    assert b"Unresolved Collaboration Actions" in ui.data
    assert b"Evidence" in ui.data and b"Closure" in ui.data and b"Archive" in ui.data
    assert b"mention never grants access" in ui.data
    assert api.status_code == 200
    assert api.get_json()["counts"]["participating_cases"] == 1
    assert all(user == "paul" for user, _ in captured)
    assert all(kwargs["allowed_case_ids"] == {"case-a"} for _, kwargs in captured)


def test_v26_0_release_note_and_no_migration():
    note = Path("release/V26_0_COLLABORATION_WORKSPACE.md").read_text(encoding="utf-8")
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v26_0*")
    ]
    for phrase in (
        "participating cases",
        "assigned role",
        "active collaborators",
        "pending handoffs",
        "unresolved review requests",
        "unread mentions or updates",
        "blocked collaboration items",
        "direct links",
        "access scope",
        "read-only",
        "mention never grants access",
    ):
        assert phrase in note
    assert migrations == []
