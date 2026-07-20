from __future__ import annotations

from typing import Any

from .canonical_observation_v36_2 import current_observations
from .claim_verification_v36_5 import current_verifications
from .dossier_synthesis_v36_7 import current_snapshots
from .entity_candidate_resolution_v36_3 import current_candidates
from .relationship_timeline_v36_6 import current_relationship_assessments
from .source_independence_v36_4 import current_independence_assessments
from .source_registry_v36_1 import current_sources

SCHEMA = "socmint.entity_accuracy_workspace.v36_8"
VERSION = "v36.8.0"


def _counts(items: list[dict[str, Any]], key: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for item in items:
        value = str(item.get(key) or "unknown")
        result[value] = result.get(value, 0) + 1
    return dict(sorted(result.items()))


def _finding(
    key: str,
    severity: str,
    count: int,
    message: str,
    next_action: str,
) -> dict[str, Any]:
    return {
        "key": key,
        "severity": severity,
        "count": count,
        "message": message,
        "next_action": next_action,
    }


def build_entity_accuracy_workspace() -> dict[str, Any]:
    sources = current_sources()
    observations = current_observations()
    candidates = current_candidates()
    independence = current_independence_assessments()
    verifications = current_verifications()
    relationships = current_relationship_assessments()
    snapshots = current_snapshots()

    findings: list[dict[str, Any]] = []
    missing_reliability = sum(
        1 for item in sources if not item.get("reliability_assessed")
    )
    quarantined = sum(
        1 for item in observations if item.get("observation_state") == "quarantined"
    )
    undecided = sum(1 for item in candidates if not item.get("decision_recorded"))
    tied = sum(
        1 for item in verifications if (item.get("ranking") or {}).get("tie_at_top")
    )
    disputed = sum(
        1 for item in verifications if item.get("unresolved_conflict_ids")
    )
    unassessed_independence = sum(
        1
        for item in verifications
        if int((item.get("independence_context") or {}).get("score") or 0) == 0
        and len(item.get("source_ids") or []) > 1
    )
    if missing_reliability:
        findings.append(
            _finding(
                "source_reliability_pending",
                "attention",
                missing_reliability,
                "Registered sources lack a claim-type reliability profile.",
                "Assess source reliability for the intended claim type.",
            )
        )
    if quarantined:
        findings.append(
            _finding(
                "canonical_observations_quarantined",
                "attention",
                quarantined,
                "Canonical observations remain quarantined.",
                "Review preserved captures before accepting or rejecting them.",
            )
        )
    if undecided:
        findings.append(
            _finding(
                "entity_candidates_waiting_decision",
                "attention",
                undecided,
                "Entity candidates have no human decision record.",
                "Record keep-separate, revision, insufficiency, or merge recommendation.",
            )
        )
    if unassessed_independence:
        findings.append(
            _finding(
                "source_independence_unassessed",
                "integrity_alert",
                unassessed_independence,
                "Multi-source claims lack an exact source-set independence assessment.",
                "Assess mirrored, derivative, syndicated, common-origin, or independent status.",
            )
        )
    if tied:
        findings.append(
            _finding(
                "alternative_ranking_tied",
                "attention",
                tied,
                "Alternative claims are tied at the highest support score.",
                "Retain the tie and collect or review additional evidence.",
            )
        )
    if disputed:
        findings.append(
            _finding(
                "verified_claims_disputed",
                "integrity_alert",
                disputed,
                "Claim verifications retain unresolved conflicts.",
                "Resolve or explicitly retain conflicts before consequential use.",
            )
        )
    if verifications and not snapshots:
        findings.append(
            _finding(
                "dossier_snapshot_missing",
                "attention",
                len(verifications),
                "Verified claims exist but no approved-contribution synthesis snapshot exists.",
                "Complete v30.5 review and v30.6 contribution approval before synthesis.",
            )
        )

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "ready",
        "read_only": True,
        "automatic_truth_assignment": False,
        "automatic_entity_merge": False,
        "automatic_dossier_publication": False,
        "summary": {
            "source_count": len(sources),
            "canonical_observation_count": len(observations),
            "entity_candidate_count": len(candidates),
            "source_independence_group_count": len(independence),
            "claim_verification_count": len(verifications),
            "relationship_timeline_count": len(relationships),
            "dossier_snapshot_count": len(snapshots),
            "finding_count": len(findings),
        },
        "source_inventory": sources,
        "observation_inventory": observations,
        "entity_candidate_inventory": candidates,
        "source_independence_inventory": independence,
        "claim_verification_inventory": verifications,
        "relationship_timeline_inventory": relationships,
        "dossier_snapshot_inventory": snapshots,
        "state_counts": {
            "observation_state": _counts(observations, "observation_state"),
            "verification_band": _counts(verifications, "confidence_band"),
            "relationship_type": _counts(relationships, "relationship_type"),
        },
        "findings": findings,
        "controls": {
            "human_review_gate": "v30.5",
            "dossier_contribution_gate": "v30.6",
            "existing_export_pipeline_remains_authoritative": True,
            "write_actions_exposed_by_workspace": [],
        },
    }
