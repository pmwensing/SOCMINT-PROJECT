from src.socmint.collection_job_contract_v29_1 import (
    create_collection_job_contract,
    transition_collection_job,
)
from src.socmint.collection_quality_v29_6 import (
    assess_collection_quality,
    review_dossier_contribution,
)
from src.socmint.collection_quality_workspace_v29_6 import (
    build_collection_quality_workspace,
)
from src.socmint.evidence_ingestion_v29_4 import (
    change_artifact_state,
    derive_observation,
    register_artifact,
)


def _accepted_artifact():
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
        idempotency_key="idem-v29-6",
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
    artifact = register_artifact(
        actor="admin",
        collection_job_id=job_id,
        attempt_number=1,
        source_reference="https://example.test/alice",
        acquired_at="2026-06-19T12:00:00+00:00",
        content_sha256="a" * 64,
        content_type="application/json",
        byte_size=42,
        acquisition_method="authorized adapter",
        provenance_metadata={"adapter": "demo"},
        reason="register",
        confirmed=True,
    )
    change_artifact_state(
        actor="admin",
        artifact_id=artifact["artifact_id"],
        to_state="accepted",
        reason="verified provenance",
        confirmed=True,
    )
    derive_observation(
        actor="admin",
        artifact_id=artifact["artifact_id"],
        observation_type="username",
        normalized_value="alice",
        confidence="high",
        derivation_method="deterministic parser",
        reason="derive",
        confirmed=True,
    )
    return artifact["artifact_id"]


def test_v29_6_quality_assessment_and_human_contribution_review(tmp_path):
    from src.socmint import database

    database.configure_database(f"sqlite:///{tmp_path / 'app.db'}")
    artifact_id = _accepted_artifact()
    assessment = assess_collection_quality(
        actor="admin", artifact_id=artifact_id, reason="quality gate", confirmed=True
    )
    assert assessment["status"] == "collection_quality_assessed"
    assert assessment["quality_score"] >= 85
    assert assessment["trust_tier"] == "trusted"
    assert assessment["dossier_mutated"] is False
    review = review_dossier_contribution(
        actor="reviewer",
        quality_assessment_id=assessment["quality_assessment_id"],
        decision="approved",
        rationale="quality and provenance verified",
        confirmed=True,
    )
    assert review["status"] == "dossier_contribution_reviewed"
    assert review["human_review_complete"] is True
    assert review["dossier_mutated"] is False
    workspace = build_collection_quality_workspace()
    assert workspace["quality_assessment_count"] == 1
    assert workspace["approved_dossier_contribution_count"] == 1
    assert workspace["automatic_dossier_contribution_available"] is False


def test_v29_6_blocks_low_trust_automatic_approval_and_duplicate_review(tmp_path):
    from src.socmint import database

    database.configure_database(f"sqlite:///{tmp_path / 'blocked.db'}")
    created = create_collection_job_contract(
        actor="admin",
        connector="demo",
        target_value="bob",
        target_type="username",
        case_id="case-b",
        entity_id="entity-b",
        source_id="source-b",
        authorization_binding={"request_id": "request-2"},
        purpose="investigation",
        idempotency_key="idem-v29-6-b",
        legacy_scan_job_id=None,
        reason="create",
        confirmed=True,
    )
    job_id = created["collection_job_id"]
    transition_collection_job(
        collection_job_id=job_id,
        actor="admin",
        to_state="authorized",
        authorization_binding={"policy_evaluation_id": "evaluation-2"},
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
    artifact = register_artifact(
        actor="admin",
        collection_job_id=job_id,
        attempt_number=1,
        source_reference="ref",
        acquired_at="2026-06-19T12:00:00+00:00",
        content_sha256="b" * 64,
        content_type="text/plain",
        byte_size=1,
        acquisition_method="manual",
        provenance_metadata={},
        reason="register",
        confirmed=True,
    )
    assessment = assess_collection_quality(
        actor="admin",
        artifact_id=artifact["artifact_id"],
        reason="quality gate",
        confirmed=True,
    )
    blocked = review_dossier_contribution(
        actor="reviewer",
        quality_assessment_id=assessment["quality_assessment_id"],
        decision="approved",
        rationale="approve",
        confirmed=True,
    )
    assert blocked["status"] == "blocked"
    held = review_dossier_contribution(
        actor="reviewer",
        quality_assessment_id=assessment["quality_assessment_id"],
        decision="held",
        rationale="needs acceptance and observations",
        confirmed=True,
    )
    assert held["status"] == "dossier_contribution_reviewed"
    duplicate = review_dossier_contribution(
        actor="reviewer",
        quality_assessment_id=assessment["quality_assessment_id"],
        decision="rejected",
        rationale="duplicate decision",
        confirmed=True,
    )
    assert duplicate["status"] == "blocked"
