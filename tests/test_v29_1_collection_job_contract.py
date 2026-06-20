from src.socmint.collection_job_contract_v29_1 import (
    create_collection_job_contract,
    transition_collection_job,
)
from src.socmint.collection_job_workspace_v29_1 import build_collection_job_workspace


def test_v29_1_collection_job_lifecycle_and_retry(tmp_path):
    from src.socmint import database

    database.configure_database(f"sqlite:///{tmp_path / 'app.db'}")
    created = create_collection_job_contract(
        actor="admin",
        connector="demo",
        target_value="alice",
        target_type="username",
        case_id="case-a",
        entity_id="entity-a",
        source_id="source-a",
        authorization_binding={"policy_id": "policy-1"},
        purpose="investigation",
        idempotency_key="idem-1",
        legacy_scan_job_id=7,
        reason="create",
        confirmed=True,
    )
    assert created["status"] == "collection_job_contract_created"
    job_id = created["collection_job_id"]
    authorized = transition_collection_job(
        collection_job_id=job_id,
        actor="admin",
        to_state="authorized",
        authorization_binding={"policy_id": "policy-1"},
        failure_category="",
        reason="authorize",
        confirmed=True,
    )
    queued = transition_collection_job(
        collection_job_id=job_id,
        actor="admin",
        to_state="queued",
        authorization_binding=None,
        failure_category="",
        reason="queue",
        confirmed=True,
    )
    running = transition_collection_job(
        collection_job_id=job_id,
        actor="admin",
        to_state="running",
        authorization_binding=None,
        failure_category="",
        reason="run",
        confirmed=True,
    )
    failed = transition_collection_job(
        collection_job_id=job_id,
        actor="admin",
        to_state="failed",
        authorization_binding=None,
        failure_category="network",
        reason="failure",
        confirmed=True,
    )
    retried = transition_collection_job(
        collection_job_id=job_id,
        actor="admin",
        to_state="queued",
        authorization_binding=None,
        failure_category="",
        reason="retry",
        confirmed=True,
    )
    assert [
        authorized["status"],
        queued["status"],
        running["status"],
        failed["status"],
        retried["status"],
    ] == ["collection_job_transitioned"] * 5
    assert failed["retry_eligible"] is True
    assert retried["attempt_number"] == 2
    result = build_collection_job_workspace()
    assert result["contract_count"] == 1
    assert result["state_counts"] == {"queued": 1}
    assert result["collection_job_event_count"] == 6
    assert result["append_only"] is True
    assert result["legacy_scan_jobs_mutated"] is False
    assert result["connector_execution_available"] is False


def test_v29_1_blocks_invalid_transition_and_duplicate_idempotency(tmp_path):
    from src.socmint import database

    database.configure_database(f"sqlite:///{tmp_path / 'blocked.db'}")
    created = create_collection_job_contract(
        actor="admin",
        connector="demo",
        target_value="alice",
        target_type="username",
        case_id="",
        entity_id="",
        source_id="source-a",
        authorization_binding={"policy_id": "policy-1"},
        purpose="investigation",
        idempotency_key="idem-1",
        legacy_scan_job_id=None,
        reason="create",
        confirmed=True,
    )
    duplicate = create_collection_job_contract(
        actor="admin",
        connector="demo",
        target_value="alice",
        target_type="username",
        case_id="",
        entity_id="",
        source_id="source-a",
        authorization_binding={"policy_id": "policy-1"},
        purpose="investigation",
        idempotency_key="idem-1",
        legacy_scan_job_id=None,
        reason="create",
        confirmed=True,
    )
    invalid = transition_collection_job(
        collection_job_id=created["collection_job_id"],
        actor="admin",
        to_state="running",
        authorization_binding=None,
        failure_category="",
        reason="skip",
        confirmed=True,
    )
    assert duplicate["status"] == "blocked"
    assert invalid["status"] == "blocked"
