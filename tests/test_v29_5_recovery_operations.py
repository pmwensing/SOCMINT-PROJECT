from datetime import datetime, timedelta, timezone

from src.socmint.collection_job_contract_v29_1 import (
    create_collection_job_contract,
    transition_collection_job,
)
from src.socmint.recovery_operations_v29_5 import (
    create_recovery_plan,
    decide_retry,
    record_operator_intervention,
    request_retry,
)
from src.socmint.recovery_operations_workspace_v29_5 import (
    build_recovery_operations_workspace,
)


def _failed_job(key="idem-v29-5"):
    created = create_collection_job_contract(
        actor="admin",
        connector="demo",
        target_value="alice",
        target_type="username",
        case_id="case-a",
        entity_id="entity-a",
        source_id="source-a",
        authorization_binding={"request_id": "request-1"},
        purpose="investigation",
        idempotency_key=key,
        legacy_scan_job_id=None,
        reason="create",
        confirmed=True,
    )
    job_id = created["collection_job_id"]
    transition_collection_job(
        collection_job_id=job_id,
        actor="admin",
        to_state="authorized",
        authorization_binding={"policy_evaluation_id": "evaluation-1"},
        failure_category="",
        reason="authorize",
        confirmed=True,
    )
    transition_collection_job(
        collection_job_id=job_id,
        actor="admin",
        to_state="queued",
        authorization_binding=None,
        failure_category="",
        reason="queue",
        confirmed=True,
    )
    transition_collection_job(
        collection_job_id=job_id,
        actor="admin",
        to_state="running",
        authorization_binding=None,
        failure_category="",
        reason="run",
        confirmed=True,
    )
    transition_collection_job(
        collection_job_id=job_id,
        actor="admin",
        to_state="failed",
        authorization_binding=None,
        failure_category="network",
        reason="network failure",
        confirmed=True,
    )
    return job_id


def test_v29_5_retry_decision_plan_and_terminal_intervention(tmp_path):
    from src.socmint import database

    database.configure_database(f"sqlite:///{tmp_path / 'app.db'}")
    job_id = _failed_job()
    now = datetime.now(timezone.utc)
    requested = request_retry(
        actor="admin",
        collection_job_id=job_id,
        idempotency_key="retry-1",
        backoff_seconds=60,
        earliest_retry_at=(now - timedelta(minutes=1)).isoformat(),
        retry_window_ends_at=(now + timedelta(hours=1)).isoformat(),
        max_attempts=3,
        reason="retry network failure",
        confirmed=True,
    )
    assert requested["status"] == "collection_retry_requested"
    assert requested["requested_attempt_number"] == 2
    assert requested["retry_execution_performed"] is False
    approved = decide_retry(
        actor="reviewer",
        retry_request_id=requested["retry_request_id"],
        approved=True,
        decision_reason="transient failure",
        confirmed=True,
    )
    assert approved["status"] == "collection_retry_decided"
    plan = create_recovery_plan(
        actor="admin",
        collection_job_id=job_id,
        retry_request_id=requested["retry_request_id"],
        plan_type="retry",
        steps=["wait for backoff", "requeue through state machine"],
        operator_required=True,
        replacement_job_id="",
        reason="controlled retry",
        confirmed=True,
    )
    assert plan["status"] == "collection_recovery_plan_created"
    assert plan["retry_execution_performed"] is False
    intervention = record_operator_intervention(
        actor="admin",
        collection_job_id=job_id,
        intervention_type="cancel",
        resolution="stop collection",
        replacement_job_id="",
        apply_terminal_transition=True,
        reason="operator cancellation",
        confirmed=True,
    )
    assert intervention["status"] == "collection_operator_intervention_recorded"
    assert intervention["intervention"]["terminal_transition_applied"] is True
    result = build_recovery_operations_workspace()
    assert result["retry_request_count"] == 1
    assert result["approved_retry_request_count"] == 1
    assert result["recovery_plan_count"] == 1
    assert result["operator_intervention_count"] == 1
    assert result["automatic_retry_execution_available"] is False
    assert result["connector_execution_available"] is False


def test_v29_5_blocks_ineligible_duplicate_and_invalid_windows(tmp_path):
    from src.socmint import database

    database.configure_database(f"sqlite:///{tmp_path / 'blocked.db'}")
    job_id = _failed_job("idem-v29-5-b")
    now = datetime.now(timezone.utc)
    invalid_window = request_retry(
        actor="admin",
        collection_job_id=job_id,
        idempotency_key="retry-b",
        backoff_seconds=0,
        earliest_retry_at=(now + timedelta(hours=2)).isoformat(),
        retry_window_ends_at=(now + timedelta(hours=1)).isoformat(),
        max_attempts=3,
        reason="retry",
        confirmed=True,
    )
    assert invalid_window["status"] == "blocked"
    first = request_retry(
        actor="admin",
        collection_job_id=job_id,
        idempotency_key="retry-c",
        backoff_seconds=0,
        earliest_retry_at="",
        retry_window_ends_at="",
        max_attempts=3,
        reason="retry",
        confirmed=True,
    )
    duplicate = request_retry(
        actor="admin",
        collection_job_id=job_id,
        idempotency_key="retry-c",
        backoff_seconds=0,
        earliest_retry_at="",
        retry_window_ends_at="",
        max_attempts=3,
        reason="retry",
        confirmed=True,
    )
    assert first["status"] == "collection_retry_requested"
    assert duplicate["status"] == "blocked"
