from __future__ import annotations

from collections import Counter
from typing import Any

from .collection_quality_v29_6 import CONTRIBUTION_STATES, TRUST_TIERS, contribution_reviews, latest_contribution_review, quality_assessments
from .evidence_ingestion_v29_4 import current_artifacts

SCHEMA = "socmint.collection_quality_workspace.v29_6"
VERSION = "v29.6.0"


def build_collection_quality_workspace() -> dict[str, Any]:
    artifacts = current_artifacts()
    assessments = quality_assessments()
    reviews = contribution_reviews()
    assessment_by_artifact = {str(item.get("artifact_id") or ""): item for item in assessments}
    queue = []
    findings = []
    for artifact in artifacts:
        artifact_id = str(artifact.get("artifact_id") or "")
        assessment = assessment_by_artifact.get(artifact_id)
        if assessment is None:
            queue.append({"artifact_id": artifact_id, "artifact_state": artifact.get("artifact_state"), "collection_job_id": artifact.get("collection_job_id"), "reason": "quality_assessment_required"})
            continue
        review = latest_contribution_review(str(assessment.get("quality_assessment_id") or ""))
        if review is None:
            queue.append({"artifact_id": artifact_id, "quality_assessment_id": assessment.get("quality_assessment_id"), "quality_score": assessment.get("quality_score"), "trust_tier": assessment.get("trust_tier"), "reason": "dossier_contribution_review_required"})
        if assessment.get("trust_tier") in {"untrusted", "limited"}:
            findings.append({"severity": "high" if assessment.get("trust_tier") == "untrusted" else "medium", "key": "low_trust_collection_output", "artifact_id": artifact_id, "quality_assessment_id": assessment.get("quality_assessment_id")})
    trust_counts = Counter(str(item.get("trust_tier") or "untrusted") for item in assessments)
    decision_counts = Counter(str(item.get("decision") or "pending_review") for item in reviews)
    approved = [item for item in reviews if item.get("decision") == "approved"]
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "ready",
        "trust_tiers": list(TRUST_TIERS),
        "contribution_states": list(CONTRIBUTION_STATES),
        "artifacts": artifacts,
        "artifact_count": len(artifacts),
        "quality_assessments": assessments,
        "quality_assessment_count": len(assessments),
        "trust_tier_counts": dict(sorted(trust_counts.items())),
        "dossier_contribution_reviews": reviews,
        "dossier_contribution_review_count": len(reviews),
        "dossier_contribution_decision_counts": dict(sorted(decision_counts.items())),
        "approved_dossier_contributions": approved,
        "approved_dossier_contribution_count": len(approved),
        "quality_review_queue": queue,
        "quality_review_queue_count": len(queue),
        "quality_findings": findings,
        "quality_finding_count": len(findings),
        "dossier_mutated": False,
        "evidence_mutated": False,
        "connector_execution_available": False,
        "automatic_dossier_contribution_available": False,
        "human_review_required": True,
        "next_action": "review_collection_quality_trust_and_dossier_contribution",
    }
