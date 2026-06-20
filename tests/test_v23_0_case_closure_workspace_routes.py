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


def test_v23_0_routes_and_ui(tmp_path, monkeypatch):
    from src.socmint import case_closure_routes_v23_0 as routes

    payload = {
        "case_id": "case-alpha",
        "status": "eligible_for_closure_review",
        "current_release_outcome": "delivered_and_acknowledged",
        "closure_eligible": True,
        "archive_ready": True,
        "blocker_count": 0,
        "blockers": [],
        "release_history": {
            "closure_summary": {"case_id": "case-alpha", "closure_ready": True}
        },
        "delivery_recovery_state": {
            "delivery_failed": False,
            "delivery_succeeded": True,
            "acknowledgement_received": True,
            "next_action": "monitor_delivery_recovery",
        },
        "retention_policies": [
            {
                "policy_id": "standard_case_retention",
                "display_name": "Standard case retention",
                "retention_years": 7,
                "archive_class": "standard",
            }
        ],
        "proposed_retention_policy": {
            "policy_id": "standard_case_retention",
            "display_name": "Standard case retention",
            "retention_years": 7,
            "archive_class": "standard",
            "description": "Retain the case for seven years.",
        },
        "supervisor_actions": [
            {
                "action": "review_closure_readiness",
                "version": "v23.1",
                "available": True,
            }
        ],
        "links": {
            "release_workspace": "/dossier-release/case-alpha",
            "release_history": "/dossier-release/case-alpha/history",
            "case_delivery_workspace": "/case-delivery?case_id=case-alpha",
        },
    }
    monkeypatch.setattr(routes, "build_case_closure_workspace", lambda case_id: payload)

    client = _app(tmp_path, monkeypatch).test_client()
    assert client.get("/api/v1/case-closure/case-alpha").status_code == 401
    with client.session_transaction() as sess:
        sess["user"] = "supervisor"

    ui = client.get("/case-closure/case-alpha")
    api = client.get("/api/v1/case-closure/case-alpha")
    assert ui.status_code == 200
    assert b"Case Closure Workspace" in ui.data
    assert b"Closure Readiness" in ui.data
    assert b"Proposed Retention Policy" in ui.data
    assert b"Supervisor Actions" in ui.data
    assert (
        b"does not create a closure decision, retention assignment, archive package, or reopen authorization"
        in ui.data
    )
    assert api.status_code == 200
    assert api.get_json()["closure_eligible"] is True
    assert api.get_json()["archive_ready"] is True


def test_v23_0_release_note_and_no_migration():
    note = Path("release/V23_0_CASE_CLOSURE_WORKSPACE.md").read_text(encoding="utf-8")
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v23_0*")
    ]
    assert "v22.6 closure summary" in note
    assert "proposed retention policy" in note
    assert "archive readiness" in note
    assert "read-oriented" in note
    assert migrations == []
