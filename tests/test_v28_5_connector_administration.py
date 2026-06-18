from src.socmint.connector_administration_events_v28_5 import register_connector, revise_connector, set_connector_enabled, update_auth_readiness
from src.socmint.connector_administration_workspace_v28_5 import build_connector_administration_workspace


def test_v28_5_connector_lifecycle_health_and_history(tmp_path, monkeypatch):
    from src.socmint import database
    from src.socmint import connector_administration_workspace_v28_5 as workspace
    database.configure_database(f"sqlite:///{tmp_path / 'app.db'}")
    created = register_connector(actor="admin", name="Example", connector_type="api", authorization_scopes=["read:cases"], rate_limit_policy={"requests_per_minute":60}, description="demo", reason="register", confirmed=True)
    assert created["status"] == "connector_registered"
    connector_id = created["connector_id"]
    readiness = update_auth_readiness(connector_id, actor="admin", auth_readiness="configured", auth_expires_at="2027-01-01T00:00:00+00:00", reason="configured", confirmed=True)
    assert readiness["status"] == "connector_auth_readiness_updated"
    enabled = set_connector_enabled(connector_id, actor="admin", enabled=True, reason="enable", confirmed=True)
    assert enabled["status"] == "connector_state_updated"
    revised = revise_connector(connector_id, actor="admin", name="Example v2", connector_type="api", authorization_scopes=["read:cases","read:evidence"], rate_limit_policy={"requests_per_minute":30}, description="updated", reason="revise", confirmed=True)
    assert revised["status"] == "connector_revised"
    monkeypatch.setattr(workspace, "_run_health", lambda: {"Example v2":{"run_count":2,"status_counts":{"success":2},"latest_status":"success","latest_run_at":"2026-06-18T00:00:00+00:00","error_count":0}})
    result = build_connector_administration_workspace()
    assert result["connector_count"] == 2
    assert result["active_connector_count"] == 1
    assert result["auth_readiness_counts"] == {"configured":1}
    assert result["connector_event_count"] == 4
    assert result["secret_values_visible"] is False
    assert result["connector_execution_available"] is False


def test_v28_5_blocks_duplicate_and_unchanged_state(tmp_path):
    from src.socmint import database
    database.configure_database(f"sqlite:///{tmp_path / 'blocked.db'}")
    created = register_connector(actor="admin", name="Example", connector_type="api", authorization_scopes=[], rate_limit_policy={}, description="", reason="register", confirmed=True)
    duplicate = register_connector(actor="admin", name="Example", connector_type="api", authorization_scopes=[], rate_limit_policy={}, description="", reason="register", confirmed=True)
    assert duplicate["status"] == "blocked"
    unchanged = set_connector_enabled(created["connector_id"], actor="admin", enabled=False, reason="same", confirmed=True)
    assert unchanged["status"] == "blocked"
