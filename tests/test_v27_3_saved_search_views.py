from src.socmint.saved_search_view_events_v27_3 import create_view, current_views, deactivate_view, revise_view, visible_views
from src.socmint.saved_search_views_workspace_v27_3 import run_saved_view


def test_v27_3_create_revise_visibility_and_deactivate(tmp_path, monkeypatch):
    from src.socmint import database
    database.configure_database(f"sqlite:///{tmp_path / 'app.db'}")
    created = create_view(name="My Findings", owner="alice", query="reuse", filters={"record_types": ["finding"]}, visibility="private", confirmed=True)
    assert created["status"] == "saved_view_created"
    duplicate = create_view(name="my findings", owner="alice", query="x", filters={}, visibility="private", confirmed=True)
    assert duplicate["status"] == "blocked"
    revised = revise_view(created["saved_view_id"], actor="alice", name="My Findings v2", query="reuse", filters={"record_types": ["finding"], "statuses": ["open"]}, visibility="shared", description="team preset", reason="add status", confirmed=True)
    assert revised["status"] == "saved_view_revised"
    assert revised["revision"] == 2
    assert revised["prior_saved_view_mutated"] is False
    assert any(item["saved_view_id"] == revised["saved_view_id"] for item in visible_views("bob"))
    deactivated = deactivate_view(revised["saved_view_id"], actor="alice", reason="obsolete", confirmed=True)
    assert deactivated["status"] == "saved_view_deactivated"
    states = {item["saved_view_id"]: item["view_status"] for item in current_views()}
    assert states[created["saved_view_id"]] == "superseded"
    assert states[revised["saved_view_id"]] == "deactivated"


def test_v27_3_run_uses_current_access_scope(monkeypatch):
    from src.socmint import saved_search_views_workspace_v27_3 as workspace
    view = {"saved_view_id": "view-1", "view_status": "active", "definition": {"query": "alpha", "filters": {"record_types": ["case"]}}}
    monkeypatch.setattr(workspace, "find_view", lambda view_id, user: view)
    captured = {}
    def build(query, **kwargs):
        captured.update({"query": query, **kwargs})
        return {"status": "ready", "results": []}
    monkeypatch.setattr(workspace, "build_advanced_search_filters", build)
    result = run_saved_view("view-1", user_identity="alice", allowed_case_ids={"case-a"}, limit=25)
    assert result["status"] == "saved_view_executed"
    assert captured["allowed_case_ids"] == {"case-a"}
    assert captured["limit"] == 25
    assert result["saved_view_grants_access"] is False
    assert result["saved_view_mutated"] is False
