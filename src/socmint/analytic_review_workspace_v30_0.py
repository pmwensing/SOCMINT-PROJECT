from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from . import database
from .analytic_confidence_v30_4 import confidence_assessments
from .analytic_conflict_v30_3 import current_conflicts
from .claim_source_linkage_v30_2 import claim_linkages
from .collection_quality_v29_6 import contribution_reviews, quality_assessments
from .corroboration_claim_v30_1 import current_claims
from .evidence_ingestion_v29_4 import current_artifacts, observations
from .report_review import list_enrichment_review_items, review_summary, safe_rows, table_exists

SCHEMA = "socmint.analytic_review_workspace.v30_0"
VERSION = "v30.4.0"


def _claim_inventory() -> list[dict[str, Any]]:
    if not table_exists("spine_dossier_assertions"):
        return []
    return safe_rows("SELECT id, subject_id, assertion_type, normalized_value, confidence, validation_state, created_at FROM spine_dossier_assertions ORDER BY id DESC LIMIT 500")


def _review_decisions() -> list[dict[str, Any]]:
    if not table_exists("review_decisions"):
        return []
    return safe_rows("SELECT * FROM review_decisions ORDER BY id DESC LIMIT 500")


def _contradictions(claims: list[dict[str, Any]], obs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], set[str]] = defaultdict(set)
    sources: dict[tuple[str, str], list[str]] = defaultdict(list)
    for item in claims:
        subject = str(item.get("entity_id") or item.get("subject_id") or "")
        kind = str(item.get("claim_type") or item.get("assertion_type") or "unknown")
        value = str(item.get("normalized_value") or "").strip()
        if value:
            grouped[(subject, kind)].add(value)
            sources[(subject, kind)].append(str(item.get("claim_id") or f"assertion:{item.get('id')}"))
    for item in obs:
        binding = item.get("contract_binding") or {}
        observation = item.get("observation") or {}
        subject = str(binding.get("entity_id") or binding.get("case_id") or item.get("artifact_id") or "")
        kind = str(item.get("observation_type") or observation.get("observation_type") or "unknown")
        value = str(item.get("normalized_value") or observation.get("normalized_value") or "").strip()
        if value:
            grouped[(subject, kind)].add(value)
            sources[(subject, kind)].append(str(item.get("observation_id") or item.get("artifact_event_id") or "observation"))
    return [{"subject_key": subject, "claim_type": kind, "distinct_values": sorted(values), "source_refs": sources[(subject, kind)], "status": "requires_human_review"} for (subject, kind), values in grouped.items() if len(values) > 1]


def build_analytic_review_workspace() -> dict[str, Any]:
    database.ensure_configured()
    artifacts = current_artifacts()
    obs = observations()
    legacy_claims = _claim_inventory()
    v30_claims = current_claims()
    linkages = claim_linkages()
    conflicts = current_conflicts()
    v30_confidence = confidence_assessments()
    claims = [*legacy_claims, *v30_claims]
    quality = quality_assessments()
    contribution = contribution_reviews()
    review_items = list_enrichment_review_items(limit=500)
    decisions = _review_decisions()
    detected_contradictions = _contradictions(claims, obs)

    confidence_records = [
        {"record_type": "claim", "record_id": f"assertion:{item.get('id')}", "confidence": item.get("confidence"), "review_state": item.get("validation_state")}
        for item in legacy_claims if item.get("confidence") is not None
    ] + [
        {"record_type": "review_item", "record_id": item.id, "confidence": item.confidence, "review_state": item.status}
        for item in review_items if item.confidence is not None
    ] + [
        {"record_type": "collection_quality", "record_id": item.get("quality_assessment_id"), "confidence": item.get("quality_score"), "review_state": item.get("trust_tier")}
        for item in quality
    ] + [
        {"record_type": "analytic_claim", "record_id": item.get("confidence_assessment_id"), "claim_id": item.get("claim_id"), "confidence": item.get("confidence_score"), "review_state": item.get("confidence_band"), "explanation": item.get("explanation")}
        for item in v30_confidence
    ]

    approved = [item for item in contribution if item.get("decision") == "approved"]
    held = [item for item in contribution if item.get("decision") == "held"]
    rejected = [item for item in contribution if item.get("decision") == "rejected"]
    pending_quality = [item for item in quality if not any(r.get("quality_assessment_id") == item.get("quality_assessment_id") for r in contribution)]
    linked_claim_ids = {str(item.get("claim_id")) for item in linkages}
    confidence_claim_ids = {str(item.get("claim_id")) for item in v30_confidence}
    unlinked_claims = [item for item in v30_claims if item.get("claim_state") == "proposed" and str(item.get("claim_id")) not in linked_claim_ids]
    unassessed_claims = [item for item in v30_claims if item.get("claim_state") == "proposed" and str(item.get("claim_id")) in linked_claim_ids and str(item.get("claim_id")) not in confidence_claim_ids]
    unresolved_conflicts = [item for item in conflicts if item.get("resolution") == "unresolved"]

    findings: list[dict[str, Any]] = []
    if detected_contradictions:
        findings.append({"severity": "high", "key": "contradictory_claim_values_present", "count": len(detected_contradictions)})
    if unresolved_conflicts:
        findings.append({"severity": "high", "key": "analytic_conflicts_unresolved", "count": len(unresolved_conflicts)})
    unreviewed_claims = [item for item in legacy_claims if str(item.get("validation_state") or "").lower() in {"", "pending", "unreviewed", "needs_review"}] + [item for item in v30_claims if item.get("claim_state") == "proposed"]
    if unreviewed_claims:
        findings.append({"severity": "medium", "key": "claims_require_review", "count": len(unreviewed_claims)})
    if unlinked_claims:
        findings.append({"severity": "medium", "key": "corroboration_claims_missing_source_linkage", "count": len(unlinked_claims)})
    if unassessed_claims:
        findings.append({"severity": "medium", "key": "linked_claims_missing_confidence_assessment", "count": len(unassessed_claims)})
    missing_confidence = [item for item in legacy_claims if item.get("confidence") is None]
    if missing_confidence:
        findings.append({"severity": "medium", "key": "claims_missing_confidence", "count": len(missing_confidence)})
    if pending_quality:
        findings.append({"severity": "medium", "key": "quality_assessments_pending_contribution_review", "count": len(pending_quality)})

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "ready",
        "read_only": True,
        "evidence_inventory": artifacts,
        "evidence_count": len(artifacts),
        "observation_inventory": obs,
        "observation_count": len(obs),
        "claim_inventory": claims,
        "claim_count": len(claims),
        "legacy_claim_count": len(legacy_claims),
        "corroboration_claim_inventory": v30_claims,
        "corroboration_claim_count": len(v30_claims),
        "claim_source_linkage_inventory": linkages,
        "claim_source_linkage_count": len(linkages),
        "unlinked_corroboration_claim_count": len(unlinked_claims),
        "analytic_conflict_inventory": conflicts,
        "analytic_conflict_count": len(conflicts),
        "unresolved_analytic_conflict_count": len(unresolved_conflicts),
        "analytic_confidence_inventory": v30_confidence,
        "analytic_confidence_count": len(v30_confidence),
        "unassessed_linked_claim_count": len(unassessed_claims),
        "confidence_inventory": confidence_records,
        "confidence_record_count": len(confidence_records),
        "review_item_inventory": [item.__dict__ for item in review_items],
        "review_item_count": len(review_items),
        "review_decision_inventory": decisions,
        "review_decision_count": len(decisions),
        "contradiction_inventory": detected_contradictions,
        "contradiction_count": len(detected_contradictions),
        "dossier_contribution_inventory": contribution,
        "dossier_contribution_summary": {"approved": len(approved), "held": len(held), "rejected": len(rejected), "pending_review": len(pending_quality)},
        "quality_assessment_count": len(quality),
        "review_summary": review_summary(),
        "confidence_state_counts": dict(sorted(Counter(str(item.get("review_state") or "unknown") for item in confidence_records).items())),
        "analytic_findings": findings,
        "analytic_finding_count": len(findings),
        "raw_evidence_mutated": False,
        "observations_mutated": False,
        "claims_mutated": False,
        "review_decisions_mutated": False,
        "dossier_mutated": False,
        "connector_execution_performed": False,
        "next_action": "human_analytic_review",
    }
