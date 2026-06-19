from datetime import datetime, timedelta, timezone

from src.socmint.collection_operations_workspace_v29_0 import build_collection_operations_workspace


def test_v29_0_aggregates_collection_jobs_outputs_and_provenance(monkeypatch):
    from src.socmint import collection_operations_workspace_v29_0 as workspace
    old = datetime.now(timezone.utc) - timedelta(hours=48)
    monkeypatch.setattr(workspace, "_scan_jobs", lambda: [
        {"job_id":1,"target_id":10,"target_value":"alice","target_type":"username","tools":["demo"],"enrich":False,"status":"failed","requested_by":"admin","error_present":True,"created_at":old.isoformat(),"started_at":old.isoformat(),"finished_at":None,"_created_at":old,"_started_at":old,"_finished_at":None},
        {"job_id":2,"target_id":11,"target_value":"bob","target_type":"username","tools":["demo"],"enrich":True,"status":"running","requested_by":None,"error_present":False,"created_at":old.isoformat(),"started_at":old.isoformat(),"finished_at":None,"_created_at":old,"_started_at":old,"_finished_at":None},
    ])
    monkeypatch.setattr(workspace, "_connector_runs", lambda: [
        {"run_id":100,"target_id":10,"target_value":"alice","target_type":"username","connector":"demo","status":"success","raw_result_present":True,"raw_result_size":42,"error_present":False,"created_at":old.isoformat(),"_created_at":old},
        {"run_id":101,"target_id":10,"target_value":"alice","target_type":"username","connector":"demo","status":"success","raw_result_present":True,"raw_result_size":43,"error_present":False,"created_at":old.isoformat(),"_created_at":old},
    ])
    monkeypatch.setattr(workspace, "_findings", lambda: [
        {"finding_id":1,"connector_run_id":100,"target_id":10,"source":"demo","type":"profile","confidence":"0.8","context_present":True,"created_at":old.isoformat()},
    ])
    monkeypatch.setattr(workspace, "_results", lambda: [
        {"result_id":1,"target_id":10,"tool_id":1,"data_present":True,"data_size":20,"timestamp":old.isoformat()},
    ])
    monkeypatch.setattr(workspace, "_media", lambda: [
        {"media_id":1,"target_id":10,"profile_id":None,"source_present":True,"path_present":True,"checksum_present":True,"content_type":"image/png","created_at":old.isoformat()},
    ])
    monkeypatch.setattr(workspace, "_optional_table_summary", lambda: {
        "spine_subjects":{"available":True,"record_count":1,"columns":[]},
        "spine_seeds":{"available":True,"record_count":1,"columns":[]},
        "spine_connector_runs":{"available":True,"record_count":2,"columns":[]},
        "spine_observations":{"available":True,"record_count":3,"columns":[]},
        "spine_dossier_assertions":{"available":True,"record_count":1,"columns":[]},
    })
    result = build_collection_operations_workspace(stale_after_hours=24)
    assert result["status"] == "ready"
    assert result["job_count"] == 2
    assert result["collection_run_count"] == 2
    assert result["stale_job_count"] == 1
    assert result["retry_eligible_count"] == 1
    assert result["duplicate_run_group_count"] == 1
    assert result["evidence_summary"]["finding_count"] == 1
    assert result["observation_summary"]["spine_observation_count"] == 3
    assert result["provenance_summary"]["incomplete_connector_run_count"] == 0
    assert result["dossier_value_summary"]["contributing_run_count"] == 1
    assert result["dossier_value_summary"]["unproven_run_count"] == 1
    keys = {item["key"] for item in result["operator_findings"]}
    assert {"collection_job_failed","collection_job_stale","duplicate_collection_runs","collection_without_requesting_actor"}.issubset(keys)
    assert result["read_only"] is True
    assert result["connector_execution_available"] is False
    assert result["job_mutation_available"] is False
    assert result["retry_execution_available"] is False
    assert result["secret_values_visible"] is False
    assert result["case_access_scope_changed"] is False
    assert result["evidence_rewritten"] is False


def test_v29_0_empty_workspace_is_stable(monkeypatch):
    from src.socmint import collection_operations_workspace_v29_0 as workspace
    monkeypatch.setattr(workspace, "_scan_jobs", lambda: [])
    monkeypatch.setattr(workspace, "_connector_runs", lambda: [])
    monkeypatch.setattr(workspace, "_findings", lambda: [])
    monkeypatch.setattr(workspace, "_results", lambda: [])
    monkeypatch.setattr(workspace, "_media", lambda: [])
    monkeypatch.setattr(workspace, "_optional_table_summary", lambda: {})
    result = build_collection_operations_workspace()
    assert result["status"] == "ready"
    assert result["job_count"] == 0
    assert result["collection_run_count"] == 0
    assert result["operator_finding_count"] == 0
