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


def _workspace():
    return {
        "schema": "socmint.dossier_supervisor_approval.v21_5",
        "version": "v21.5.0",
        "case_id": "case-alpha",
        "subject_id": 42,
        "status": "reviewable",
        "review_ready": True,
        "can_approve": True,
        "can_return": True,
        "can_hold": True,
        "quality_review": {
            "status": "ready",
            "ready": True,
            "review_id": "review-1",
            "review_sha256": "a" * 64,
            "blocker_count": 0,
            "ready_section_count": 1,
            "section_count": 1,
        },
        "latest_decision": None,
    }


def test_v21_5_routes_and_ui(tmp_path, monkeypatch):
    from src.socmint import dossier_supervisor_approval_routes_v21_5 as routes

    monkeypatch.setattr(
        routes, "build_supervisor_approval_workspace", lambda *a, **k: _workspace()
    )
    monkeypatch.setattr(
        routes,
        "record_supervisor_dossier_decision",
        lambda *a, **k: {
            "status": "approved",
            "approval_record_id": 11,
            "next_action": "prepare_final_export_package",
        },
    )
    client = _app(tmp_path, monkeypatch).test_client()
    with client.session_transaction() as sess:
        sess["user"] = "supervisor"
        sess["_csrf_token"] = "test-csrf"
    api = client.get(
        "/api/v1/dossier-assembly/case-alpha/supervisor-approval?subject_id=42"
    )
    ui = client.get("/dossier-assembly/case-alpha/supervisor-approval?subject_id=42")
    saved = client.post(
        "/api/v1/dossier-assembly/case-alpha/supervisor-decision?subject_id=42",
        json={"decision": "approve", "note": "ready"},
        headers={"X-CSRF-Token": "test-csrf"},
    )
    assert api.status_code == 200
    assert ui.status_code == 200
    assert b"Supervisor Dossier Approval" in ui.data
    assert b"Source Quality Review" in ui.data
    assert b"Record supervisor decision" in ui.data
    assert saved.status_code == 200
    assert saved.get_json()["approval_record_id"] == 11


def test_v21_5_release_note_client_and_no_migration():
    note = Path("release/V21_5_SUPERVISOR_DOSSIER_APPROVAL.md").read_text(
        encoding="utf-8"
    )
    script = Path("src/socmint/static/dossier_supervisor_approval_v21_5.js").read_text(
        encoding="utf-8"
    )
    migrations = [
        p
        for d in (Path("migrations"), Path("alembic"))
        if d.exists()
        for p in d.rglob("*v21_5*")
    ]
    assert "ready review" in note
    assert "approve, return, or hold" in note
    assert "final export" in note
    assert "supervisor-decision" in script
    assert migrations == []
