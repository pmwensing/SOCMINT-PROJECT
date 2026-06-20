from __future__ import annotations

from collections import Counter
from typing import Any

from .evidence_ingestion_v29_4 import (
    ARTIFACT_STATES,
    SCHEMA,
    VERSION,
    current_artifacts,
    history,
    observations,
)


def build_evidence_ingestion_workspace() -> dict[str, Any]:
    artifacts = current_artifacts()
    events = history()
    derived = observations()
    state_counts = Counter(
        str(item.get("artifact_state") or "unknown") for item in artifacts
    )
    duplicates = [item for item in artifacts if item.get("duplicate_of_artifact_id")]
    quarantined = [
        item for item in artifacts if item.get("artifact_state") == "quarantined"
    ]
    rejected = [item for item in artifacts if item.get("artifact_state") == "rejected"]
    accepted = [item for item in artifacts if item.get("artifact_state") == "accepted"]
    incomplete = [
        item for item in artifacts if not item.get("chain_of_custody_complete")
    ]
    findings = []
    for item in artifacts:
        if not item.get("content_sha256"):
            findings.append(
                {
                    "severity": "critical",
                    "key": "artifact_content_hash_missing",
                    "artifact_id": item.get("artifact_id"),
                }
            )
        if not item.get("acquisition_sha256"):
            findings.append(
                {
                    "severity": "critical",
                    "key": "artifact_acquisition_hash_missing",
                    "artifact_id": item.get("artifact_id"),
                }
            )
        if not item.get("contract_binding_sha256"):
            findings.append(
                {
                    "severity": "high",
                    "key": "collection_attempt_binding_missing",
                    "artifact_id": item.get("artifact_id"),
                }
            )
        if item.get("duplicate_of_artifact_id"):
            findings.append(
                {
                    "severity": "medium",
                    "key": "duplicate_artifact_detected",
                    "artifact_id": item.get("artifact_id"),
                    "duplicate_of_artifact_id": item.get("duplicate_of_artifact_id"),
                }
            )
        if item.get("artifact_state") == "registered":
            findings.append(
                {
                    "severity": "low",
                    "key": "artifact_pending_acceptance_review",
                    "artifact_id": item.get("artifact_id"),
                }
            )
        if item.get("artifact_state") == "quarantined":
            findings.append(
                {
                    "severity": "high",
                    "key": "artifact_quarantined",
                    "artifact_id": item.get("artifact_id"),
                }
            )
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "ready",
        "artifact_states": list(ARTIFACT_STATES),
        "artifacts": artifacts,
        "artifact_count": len(artifacts),
        "artifact_state_counts": dict(sorted(state_counts.items())),
        "accepted_artifacts": accepted,
        "accepted_artifact_count": len(accepted),
        "quarantined_artifacts": quarantined,
        "quarantined_artifact_count": len(quarantined),
        "rejected_artifacts": rejected,
        "rejected_artifact_count": len(rejected),
        "duplicate_artifacts": duplicates,
        "duplicate_artifact_count": len(duplicates),
        "chain_of_custody_incomplete": incomplete,
        "chain_of_custody_incomplete_count": len(incomplete),
        "derived_observations": derived[-250:],
        "derived_observation_count": len(derived),
        "ingestion_findings": findings,
        "ingestion_finding_count": len(findings),
        "provenance_history": events[-300:],
        "provenance_event_count": len(events),
        "raw_content_visible": False,
        "raw_content_recorded": False,
        "legacy_evidence_mutated": False,
        "connector_output_mutated": False,
        "connector_execution_available": False,
        "case_access_scope_changed": False,
        "next_action": "review_evidence_ingestion_and_provenance",
    }
