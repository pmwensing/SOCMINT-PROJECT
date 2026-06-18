from datetime import datetime, timedelta, timezone

from src.socmint.platform_operations_events_v28_6 import acknowledge_incident, open_incident, resolve_incident
from src.socmint.platform_operations_workspace_v28_6 import build_platform_operations_workspace


def test_v28_6_health_findings_incidents_and_history(tmp_path, monkeypatch):
    from src.socmint import database
    from src.socmint import platform_operations_workspace_v28_6 as workspace
    database.configure_database(f"sqlite:///{tmp_path / 'app.db'}")
    opened = open_incident(actor="admin", title="Queue failure", severity="high", component="jobs", description="failure", source_binding={"job_id":1}, reason="investigate", confirmed=True)
    assert opened["status"] == "operational_incident_opened"
    acknowledged = acknowledge_incident(opened["incident_id"], actor="admin", note="working", reason="ack", confirmed=True)
    assert acknowledged["status"] == "operational_incident_acknowledged"
    old = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
    monkeypatch.setattr(workspace, "_jobs", lambda: [{"job_id":1,"status":"failed","created_at":old,"updated_at":old,"started_at":old,"completed_at":None,"error_present":True,"job_type":"scan"},{"job_id":2,"status":"running","created_at":old,"updated_at":old,"started_at":old,"completed_at":None,"error_present":False,"job_type":"scan"}])
    monkeypatch.setattr(workspace, "_connector_runs", lambda: [{"run_id":1,"connector":"demo","status":"failed","created_at":old,"error_present":True}])
    monkeypatch.setattr(workspace, "_audit_snapshot", lambda: {"record_count":10,"first_record_id":1,"last_record_id":11,"id_gap_count":1,"id_gaps":[{"after_id":5,"before_id":7,"missing_count":1}],"action_counts":{},"actor_counts":{},"latest_recorded_at":old})
    monkeypatch.setattr(workspace, "_storage_state", lambda: {"path_configured":True,"path_exists":True,"path_writable":True,"path_value_exposed":False})
    monkeypatch.setattr(workspace, "_configuration_state", lambda: {"variables":{},"secret_values_exposed":False,"configuration_mutated":False})
    monkeypatch.setattr(workspace.database, "check_ready", lambda: True)
    result = build_platform_operations_workspace(stale_after_hours=24)
    assert result["overall_status"] == "attention_required"
    assert result["job_health"]["failed_job_count"] == 1
    assert result["job_health"]["stalled_job_count"] == 1
    assert result["audit_log_continuity"]["id_gap_count"] == 1
    assert result["open_operational_incident_count"] == 1
    assert result["job_execution_available"] is False
    assert result["configuration_mutation_available"] is False
    assert result["audit_log_mutation_available"] is False
    resolved = resolve_incident(opened["incident_id"], actor="admin", resolution="fixed", reason="complete", confirmed=True)
    assert resolved["status"] == "operational_incident_resolved"


def test_v28_6_blocks_invalid_incident_and_duplicate_resolution(tmp_path):
    from src.socmint import database
    database.configure_database(f"sqlite:///{tmp_path / 'blocked.db'}")
    invalid = open_incident(actor="admin", title="Bad", severity="unknown", component="jobs", description="", source_binding={}, reason="test", confirmed=True)
    assert invalid["status"] == "blocked"
    opened = open_incident(actor="admin", title="Valid", severity="low", component="jobs", description="", source_binding={}, reason="test", confirmed=True)
    first = resolve_incident(opened["incident_id"], actor="admin", resolution="done", reason="close", confirmed=True)
    assert first["status"] == "operational_incident_resolved"
    second = resolve_incident(opened["incident_id"], actor="admin", resolution="again", reason="close", confirmed=True)
    assert second["status"] == "blocked"
