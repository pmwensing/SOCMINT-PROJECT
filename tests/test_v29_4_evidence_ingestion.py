from src.socmint.collection_job_contract_v29_1 import (
    create_collection_job_contract,
    transition_collection_job,
)
from src.socmint.evidence_ingestion_v29_4 import (
    change_artifact_state,
    derive_observation,
    register_artifact,
)
from src.socmint.evidence_ingestion_workspace_v29_4 import (
    build_evidence_ingestion_workspace,
)


def _running_job():
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
        idempotency_key="idem-v29-4",
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
    return job_id


def test_v29_4_artifact_acceptance_observation_and_duplicate(tmp_path):
    from src.socmint import database

    database.configure_database(f"sqlite:///{tmp_path / 'app.db'}")
    job_id = _running_job()
    artifact = register_artifact(
        actor="admin",
        collection_job_id=job_id,
        attempt_number=1,
        source_reference="source://demo/alice",
        acquired_at="2026-06-19T12:00:00+00:00",
        content_sha256="a" * 64,
        content_type="application/json",
        byte_size=128,
        acquisition_method="adapter",
        provenance_metadata={"connector": "demo"},
        reason="register",
        confirmed=True,
    )
    assert artifact["status"] == "evidence_artifact_registered"
    assert artifact["initial_state"] == "registered"
    assert artifact["chain_of_custody_complete"] is True
    assert artifact["raw_content_recorded"] is False
    accepted = change_artifact_state(
        actor="admin",
        artifact_id=artifact["artifact_id"],
        to_state="accepted",
        reason="reviewed",
        confirmed=True,
    )
    assert accepted["status"] == "evidence_artifact_state_changed"
    observation = derive_observation(
        actor="admin",
        artifact_id=artifact["artifact_id"],
        observation_type="profile",
        normalized_value={"username": "alice"},
        confidence="0.9",
        derivation_method="normalized_adapter_output",
        reason="derive",
        confirmed=True,
    )
    assert observation["status"] == "evidence_observation_derived"
    duplicate = register_artifact(
        actor="admin",
        collection_job_id=job_id,
        attempt_number=1,
        source_reference="source://demo/alice-copy",
        acquired_at="2026-06-19T12:01:00+00:00",
        content_sha256="a" * 64,
        content_type="application/json",
        byte_size=128,
        acquisition_method="adapter",
        provenance_metadata={"connector": "demo"},
        reason="register duplicate",
        confirmed=True,
    )
    assert duplicate["status"] == "evidence_artifact_registered"
    assert duplicate["initial_state"] == "quarantined"
    assert duplicate["duplicate_of_artifact_id"] == artifact["artifact_id"]
    result = build_evidence_ingestion_workspace()
    assert result["artifact_count"] == 2
    assert result["accepted_artifact_count"] == 1
    assert result["quarantined_artifact_count"] == 1
    assert result["duplicate_artifact_count"] == 1
    assert result["derived_observation_count"] == 1
    assert result["chain_of_custody_incomplete_count"] == 0
    assert result["raw_content_visible"] is False
    assert result["legacy_evidence_mutated"] is False
    assert result["connector_output_mutated"] is False


def test_v29_4_blocks_invalid_hash_attempt_and_unaccepted_observation(tmp_path):
    from src.socmint import database

    database.configure_database(f"sqlite:///{tmp_path / 'blocked.db'}")
    job_id = _running_job()
    invalid_hash = register_artifact(
        actor="admin",
        collection_job_id=job_id,
        attempt_number=1,
        source_reference="source://demo/alice",
        acquired_at="2026-06-19T12:00:00+00:00",
        content_sha256="bad",
        content_type="application/json",
        byte_size=1,
        acquisition_method="adapter",
        provenance_metadata={},
        reason="register",
        confirmed=True,
    )
    wrong_attempt = register_artifact(
        actor="admin",
        collection_job_id=job_id,
        attempt_number=2,
        source_reference="source://demo/alice",
        acquired_at="2026-06-19T12:00:00+00:00",
        content_sha256="b" * 64,
        content_type="application/json",
        byte_size=1,
        acquisition_method="adapter",
        provenance_metadata={},
        reason="register",
        confirmed=True,
    )
    assert invalid_hash["status"] == "blocked"
    assert wrong_attempt["status"] == "blocked"
    artifact = register_artifact(
        actor="admin",
        collection_job_id=job_id,
        attempt_number=1,
        source_reference="source://demo/alice",
        acquired_at="2026-06-19T12:00:00+00:00",
        content_sha256="c" * 64,
        content_type="application/json",
        byte_size=1,
        acquisition_method="adapter",
        provenance_metadata={},
        reason="register",
        confirmed=True,
    )
    observation = derive_observation(
        actor="admin",
        artifact_id=artifact["artifact_id"],
        observation_type="profile",
        normalized_value="alice",
        confidence="0.5",
        derivation_method="manual",
        reason="derive",
        confirmed=True,
    )
    assert observation["status"] == "blocked"
