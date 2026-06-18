from src.socmint.team_organization_events_v28_3 import append_team_event, create_team, revise_team
from src.socmint.team_organization_workspace_v28_3 import build_team_organization_workspace


def test_v28_3_team_lifecycle_structure_and_history(tmp_path, monkeypatch):
    from src.socmint import database
    from src.socmint import team_organization_workspace_v28_3 as workspace
    database.configure_database(f"sqlite:///{tmp_path / 'app.db'}")
    created = create_team(actor="admin", name="Investigations", description="Primary team", reason="create", confirmed=True)
    assert created["status"] == "team_created"
    team_id = created["team_id"]
    assert append_team_event(team_id, actor="admin", event_type="team_member_added", username="alice", reason="assign", confirmed=True)["status"] == "team_updated"
    assert append_team_event(team_id, actor="admin", event_type="team_supervisor_assigned", supervisor_username="bob", reason="lead", confirmed=True)["status"] == "team_updated"
    assert append_team_event(team_id, actor="admin", event_type="team_scope_bound", organizational_scope="national", ownership_boundaries=["case-intake"], reason="scope", confirmed=True)["status"] == "team_updated"
    assert append_team_event(team_id, actor="admin", event_type="team_workload_group_set", workload_group="priority", reason="workload", confirmed=True)["status"] == "team_updated"
    revised = revise_team(team_id, actor="admin", name="Investigations North", description="Updated", reason="revise", confirmed=True)
    assert revised["status"] == "team_revised"
    monkeypatch.setattr(workspace, "_users", lambda: [{"username":"alice","role":"analyst","is_admin":False,"is_active":True},{"username":"bob","role":"supervisor","is_admin":False,"is_active":True}])
    result = build_team_organization_workspace()
    assert result["active_team_count"] == 1
    assert result["member_assignment_count"] == 1
    assert result["supervised_team_count"] == 1
    assert result["organizational_scope_counts"] == {"national":1}
    assert result["workload_group_counts"] == {"priority":1}
    assert result["team_event_count"] == 6
    assert result["team_membership_grants_case_access"] is False


def test_v28_3_blocks_duplicate_team_name_and_unconfirmed_change(tmp_path):
    from src.socmint import database
    database.configure_database(f"sqlite:///{tmp_path / 'blocked.db'}")
    created = create_team(actor="admin", name="Alpha", description="", reason="create", confirmed=True)
    duplicate = create_team(actor="admin", name="Alpha", description="", reason="create", confirmed=True)
    assert duplicate["status"] == "blocked"
    result = append_team_event(created["team_id"], actor="admin", event_type="team_member_added", username="alice", reason="assign", confirmed=False)
    assert result["status"] == "blocked"
