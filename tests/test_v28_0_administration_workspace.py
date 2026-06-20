from datetime import datetime, timezone

from src.socmint.administration_workspace_v28_0 import build_administration_workspace


def test_v28_0_aggregates_users_roles_sessions_access_policy_connectors_and_health(
    monkeypatch,
):
    now = datetime.now(timezone.utc)
    events = [
        {
            "record_id": 1,
            "actor": "alice",
            "action": "user_login_success",
            "target_value": "alice",
            "ip_address": "127.0.0.1",
            "occurred_at": now.isoformat(),
            "created_at": now,
            "details": {},
        },
        {
            "record_id": 2,
            "actor": "admin",
            "action": "case_access_grant_requested",
            "target_value": "case-a",
            "ip_address": None,
            "occurred_at": now.isoformat(),
            "created_at": now,
            "details": {"status": "pending", "reason": "review"},
        },
        {
            "record_id": 3,
            "actor": "admin",
            "action": "team_membership_added",
            "target_value": "team-a",
            "ip_address": None,
            "occurred_at": now.isoformat(),
            "created_at": now,
            "details": {},
        },
        {
            "record_id": 4,
            "actor": "admin",
            "action": "policy_certification_requested",
            "target_value": "policy-a",
            "ip_address": None,
            "occurred_at": now.isoformat(),
            "created_at": now,
            "details": {"state": "requested"},
        },
    ]
    users = [
        {
            "user_id": 1,
            "username": "admin",
            "role": "admin",
            "is_admin": True,
            "is_active": True,
            "created_at": now.isoformat(),
        },
        {
            "user_id": 2,
            "username": "alice",
            "role": "analyst",
            "is_admin": False,
            "is_active": True,
            "created_at": now.isoformat(),
        },
    ]
    connectors = [
        {
            "connector": "demo",
            "run_count": 3,
            "status_counts": {"success": 3},
            "latest_status": "success",
            "latest_run_at": now.isoformat(),
            "error_count": 0,
            "credentials_exposed": False,
        }
    ]
    jobs = {
        "job_count": 2,
        "status_counts": {"completed": 2},
        "queued_count": 0,
        "running_count": 0,
        "failed_count": 0,
    }
    monkeypatch.setattr(
        "src.socmint.administration_workspace_v28_0.database.check_ready", lambda: True
    )
    result = build_administration_workspace(
        events=events, users=users, connectors=connectors, jobs=jobs
    )
    assert result["status"] == "ready"
    assert result["user_summary"]["total"] == 2
    assert result["role_summary"]["role_counts"] == {"admin": 1, "analyst": 1}
    assert result["active_session_count"] == 1
    assert result["team_summary"]["event_count"] == 1
    assert result["access_grant_summary"]["event_count"] == 1
    assert result["policy_summary"]["event_count"] == 1
    assert result["pending_admin_action_count"] == 2
    assert result["connector_summary"]["healthy_count"] == 1
    assert result["system_health"]["overall_status"] == "healthy"
    assert result["access_scope"] == {
        "mode": "administrative_read_only",
        "secrets_visible": False,
        "mutations_allowed": False,
    }
    assert len(result["workspace_sha256"]) == 64
    assert result["source_records_mutated"] is False
    assert result["case_access_scope_changed"] is False


def test_v28_0_attention_required_for_failed_jobs_or_connectors(monkeypatch):
    monkeypatch.setattr(
        "src.socmint.administration_workspace_v28_0.database.check_ready", lambda: True
    )
    result = build_administration_workspace(
        events=[],
        users=[],
        connectors=[{"connector": "bad", "latest_status": "failed", "error_count": 1}],
        jobs={"failed_count": 1},
    )
    assert result["system_health"]["overall_status"] == "attention_required"
    assert result["connector_summary"]["secrets_exposed"] is False
