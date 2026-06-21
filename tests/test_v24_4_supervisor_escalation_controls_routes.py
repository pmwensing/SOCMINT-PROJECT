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


def test_v24_4_routes_page_and_api(tmp_path, monkeypatch):
    from src.socmint import portfolio_operations_routes_v24_0 as api_routes
    from src.socmint import portfolio_supervisor_escalation_routes_v24_4 as page_routes

    state = {
        "schema": "socmint.portfolio_supervisor_escalation.v24_4",
        "version": "v24.4.0",
        "status": "attention_required",
        "items": [
            {
                "case_id": "case-alpha",
                "severity": "critical",
                "current_stage": "closure_review",
                "stage_age_hours": 160.0,
                "assignment_age_hours": 100.0,
                "blocking_reason": "delivery_acknowledgement_required",
                "owner": "owner-a",
                "assigned_reviewers": ["alice"],
                "control_history_count": 1,
                "escalated": True,
                "acknowledged": False,
                "resolved": False,
            }
        ],
        "item_count": 1,
        "source_records_mutated": False,
        "next_action": "review_supervisor_escalations",
    }
    monkeypatch.setattr(page_routes, "build_escalation_control_state", lambda: state)
    monkeypatch.setattr(api_routes, "build_escalation_control_state", lambda: state)
    monkeypatch.setattr(
        api_routes,
        "record_escalation",
        lambda *a, **k: {"status": "escalate_recorded", "action_record_id": 1},
    )
    monkeypatch.setattr(
        api_routes,
        "acknowledge_escalation",
        lambda *a, **k: {"status": "acknowledge_recorded", "action_record_id": 2},
    )
    monkeypatch.setattr(
        api_routes,
        "reassign_escalation",
        lambda *a, **k: {"status": "reassign_recorded", "action_record_id": 3},
    )
    monkeypatch.setattr(
        api_routes,
        "resolve_escalation",
        lambda *a, **k: {"status": "resolve_recorded", "action_record_id": 4},
    )

    client = _app(tmp_path, monkeypatch).test_client()
    with client.session_transaction() as sess:
        sess["_csrf_token"] = "test-csrf"

    assert client.get("/api/v1/portfolio-operations/escalations").status_code == 401
    assert client.get("/portfolio-operations/escalations").status_code in {302, 303}

    with client.session_transaction() as sess:
        sess["user"] = "supervisor"
        sess["_csrf_token"] = "test-csrf"

    page = client.get("/portfolio-operations/escalations")
    assert page.status_code == 200
    assert b"Supervisor Escalation Controls" in page.data
    assert b"case-alpha" in page.data
    assert b"delivery_acknowledgement_required" in page.data
    assert b"Case, stage, assignment, and queue records remain unchanged" in page.data

    api = client.get("/api/v1/portfolio-operations/escalations")
    assert api.status_code == 200
    assert api.get_json()["item_count"] == 1

    endpoints = {
        "escalate": {"reason": "reason", "confirmed": True},
        "acknowledge": {"confirmed": True},
        "reassign": {"assigned_reviewer": "bob", "confirmed": True},
        "resolve": {"resolution": "done", "confirmed": True},
    }
    for index, (endpoint, body) in enumerate(endpoints.items(), start=1):
        response = client.post(
            f"/api/v1/portfolio-operations/case-alpha/{endpoint}",
            json=body,
            headers={"X-CSRF-Token": "test-csrf"},
        )
        assert response.status_code == 200
        assert response.get_json()["action_record_id"] == index


def test_v24_4_release_note_client_and_no_migration():
    note = Path("release/V24_4_SUPERVISOR_ESCALATION_CONTROLS.md").read_text(
        encoding="utf-8"
    )
    script = Path(
        "src/socmint/static/portfolio_supervisor_escalations_v24_4.js"
    ).read_text(encoding="utf-8")
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v24_4*")
    ]
    assert "immutable escalation" in note
    assert "acknowledgement" in note
    assert "reassignment" in note
    assert "resolution" in note
    assert "current queue snapshot" in note
    assert "source case state" in note
    assert "underlying case, stage, and assignment events" in note
    assert "data-control" in script
    assert migrations == []
