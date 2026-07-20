from __future__ import annotations

from typing import Any

from . import database
from .analytic_conflict_v30_3 import current_conflicts
from .claim_source_linkage_v30_2 import claim_linkages
from .corroboration_claim_v30_1 import find_claim
from .dossier_assembly_workspace_v21_0 import (
    _canonical,
    _ensure_storage,
    _json_details,
    _sha,
)
from .entity_candidate_resolution_v36_3 import find_candidate
from .source_independence_v36_4 import groups_for_sources
from .source_registry_v36_1 import find_source

SCHEMA = "socmint.claim_verification.v36_5"
VERSION = "v36.5.0"
ACTION = "claim_verification_assessed"
IDENTITY_BASES = (
    "direct_verified_control",
    "reviewed_candidate",
    "case_entity_bound",
)


def blocked(key: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key}],
        "truth_assigned": False,
        "human_review_complete": False,
        "dossier_eligible": False,
        "claim_mutated": False,
        "source_mutated": False,
        "dossier_mutated": False,
    }


def _required(value: Any) -> str:
    return str(value or "").strip()


def _history() -> list[dict[str, Any]]:
    _ensure_storage()
    session = database.Session()
    try:
        rows = (
            session.query(database.AuditLog)
            .filter_by(action=ACTION)
            .order_by(
                database.AuditLog.created_at.asc(),
                database.AuditLog.id.asc(),
            )
            .all()
        )
        return [
            {
                **_json_details(row),
                "audit_record_id": row.id,
                "actor": row.actor,
                "recorded_at": (
                    row.created_at.isoformat() if row.created_at else None
                ),
            }
            for row in rows
        ]
    finally:
        session.close()


def _record(
    actor: str,
    claim_id: str,
    event: dict[str, Any],
    ip_address: str | None,
) -> dict[str, Any]:
    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=actor,
            action=ACTION,
            target_value=claim_id,
            ip_address=ip_address,
            details=_canonical(event),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return {
            **event,
            "audit_record_id": row.id,
            "actor": actor,
            "recorded_at": (
                row.created_at.isoformat() if row.created_at else None
            ),
        }
    finally:
        session.close()


def verification_history(claim_id: str | None = None) -> list[dict[str, Any]]:
    rows = _history()
    return (
        [item for item in rows if item.get("claim_id") == claim_id]
        if claim_id
        else rows
    )


def latest_verification(claim_id: str) -> dict[str, Any] | None:
    rows = verification_history(claim_id)
    return rows[-1] if rows else None


def _ranking(
    assessment: dict[str, Any],
    group: list[dict[str, Any]],
) -> dict[str, Any]:
    ordered = sorted(
        group,
        key=lambda item: (
            -int(item.get("support_score") or 0),
            str(item.get("claim_id") or ""),
        ),
    )
    position = next(
        index
        for index, item in enumerate(ordered, start=1)
        if item.get("claim_id") == assessment.get("claim_id")
    )
    top_score = int(ordered[0].get("support_score") or 0)
    top_count = sum(
        1 for item in ordered if int(item.get("support_score") or 0) == top_score
    )
    return {
        "alternative_group_id": assessment.get("alternative_group_id"),
        "position": position,
        "candidate_count": len(ordered),
        "most_likely_supported": position == 1 and top_count == 1,
        "tie_at_top": top_count > 1,
    }


def current_verifications() -> list[dict[str, Any]]:
    current: dict[str, dict[str, Any]] = {}
    for event in _history():
        claim_id = str(event.get("claim_id") or "")
        if claim_id:
            current[claim_id] = event
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in current.values():
        group_id = str(item.get("alternative_group_id") or "")
        groups.setdefault(group_id, []).append(item)
    result = []
    for item in current.values():
        group = groups.get(str(item.get("alternative_group_id") or ""), [])
        result.append({**item, "ranking": _ranking(item, group)})
    return sorted(result, key=lambda item: str(item.get("claim_id") or ""))


def find_verification(claim_id: str) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in current_verifications()
            if item.get("claim_id") == claim_id
        ),
        None,
    )


def _identity_component(
    identity_context: Any,
    *,
    case_id: str,
) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(identity_context, dict):
        return None, "identity_context_required"
    basis = _required(identity_context.get("basis"))
    reason = _required(identity_context.get("reason"))
    if basis not in IDENTITY_BASES or not reason:
        return None, "identity_context_invalid"
    if basis == "direct_verified_control":
        return {"basis": basis, "score": 100, "reason": reason}, None
    if basis == "case_entity_bound":
        return {"basis": basis, "score": 70, "reason": reason}, None
    candidate_id = _required(identity_context.get("candidate_id"))
    candidate = find_candidate(candidate_id)
    if candidate is None:
        return None, "reviewed_entity_candidate_required"
    if str(candidate.get("case_id") or "") != case_id:
        return None, "identity_candidate_case_mismatch"
    decision = candidate.get("current_decision") or {}
    if not isinstance(decision, dict) or decision.get("decision") != "recommend_merge":
        return None, "merge_recommended_entity_candidate_required"
    score = int((candidate.get("scoring") or {}).get("score") or 0)
    return {
        "basis": basis,
        "score": score,
        "reason": reason,
        "candidate_id": candidate_id,
        "candidate_assessment_sha256": candidate.get(
            "entity_candidate_assessment_sha256"
        ),
        "candidate_decision_sha256": decision.get(
            "entity_candidate_decision_sha256"
        ),
    }, None


def _source_components(
    *,
    source_ids: list[str],
    case_id: str,
    claim_type: str,
) -> tuple[dict[str, Any] | None, str | None]:
    sources = []
    reliability_scores = []
    directness_scores = []
    missing_profiles = []
    for source_id in source_ids:
        source = find_source(source_id)
        if source is None:
            return None, "source_record_required"
        if str(source.get("case_id") or "") != case_id:
            return None, "claim_source_case_mismatch"
        profiles = source.get("source_reliability_profile") or []
        profile = next(
            (
                item
                for item in profiles
                if item.get("claim_type") == claim_type
            ),
            None,
        )
        if profile is None:
            missing_profiles.append(source_id)
            reliability_scores.append(0.0)
            directness_scores.append(0.0)
        else:
            reliability_scores.append(float(profile.get("reliability_score") or 0))
            directness_scores.append(
                float((profile.get("components") or {}).get("directness") or 0)
            )
        sources.append(
            {
                "source_id": source_id,
                "source_event_sha256": source.get("source_event_sha256"),
                "capture_sha256": source.get("capture_sha256"),
                "capture_integrity_verified": source.get(
                    "capture_integrity_verified"
                )
                is True,
                "reliability_assessment_id": (
                    profile.get("source_reliability_assessment_id")
                    if profile
                    else None
                ),
            }
        )
    count = len(source_ids)
    return {
        "bindings": sources,
        "source_score": round(sum(reliability_scores) / count, 1),
        "directness_score": round(sum(directness_scores) / count, 1),
        "capture_integrity_score": round(
            sum(100 if item["capture_integrity_verified"] else 0 for item in sources)
            / count,
            1,
        ),
        "missing_claim_type_profiles": missing_profiles,
    }, None


def _independence_component(source_ids: list[str]) -> dict[str, Any]:
    if len(source_ids) < 2:
        return {
            "score": 0,
            "groups": [],
            "reason": "single_source_has_no_corroboration_independence",
        }
    groups = groups_for_sources(source_ids)
    exact = next(
        (
            item
            for item in groups
            if set(item.get("source_ids") or []) == set(source_ids)
        ),
        None,
    )
    if exact is None:
        return {
            "score": 0,
            "groups": [],
            "reason": "source_set_independence_not_assessed",
        }
    return {
        "score": int(exact.get("independence_score") or 0),
        "groups": [
            {
                "independence_group_id": exact.get("independence_group_id"),
                "relationship": exact.get("relationship"),
                "assessment_sha256": exact.get(
                    "source_independence_assessment_sha256"
                ),
            }
        ],
        "reason": "exact_source_set_independence_assessment",
    }


def _linkage_component(claim_id: str) -> tuple[dict[str, Any] | None, str | None]:
    linkages = claim_linkages(claim_id)
    if not linkages:
        return None, "claim_source_linkage_required"
    artifact_ids: set[str] = set()
    observation_ids: set[str] = set()
    for linkage in linkages:
        manifest = linkage.get("source_manifest") or {}
        artifact_ids.update(
            str(item.get("artifact_id"))
            for item in manifest.get("artifact_bindings") or []
            if item.get("artifact_id")
        )
        observation_ids.update(
            str(item.get("observation_id"))
            for item in manifest.get("observation_bindings") or []
            if item.get("observation_id")
        )
    score = 100 if artifact_ids and observation_ids else 70
    return {
        "score": score,
        "linkage_ids": [item.get("linkage_id") for item in linkages],
        "linkage_sha256": [item.get("linkage_sha256") for item in linkages],
        "artifact_count": len(artifact_ids),
        "observation_count": len(observation_ids),
    }, None


def assess_claim_verification(
    *,
    actor: str,
    claim_id: str,
    source_ids: list[str] | None,
    identity_context: dict[str, Any] | None,
    temporal_relevance_score: int,
    temporal_reason: str,
    limitations: list[str] | None,
    methodology: str,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    actor = _required(actor)
    claim_id = _required(claim_id)
    temporal_reason = _required(temporal_reason)
    methodology = _required(methodology)
    reason = _required(reason)
    normalized_sources = sorted(
        {
            _required(source_id)
            for source_id in (source_ids or [])
            if _required(source_id)
        }
    )
    normalized_limitations = sorted(
        {
            _required(item)
            for item in (limitations or [])
            if _required(item)
        }
    )
    claim = find_claim(claim_id)
    if claim is None:
        return blocked("corroboration_claim_required")
    if claim.get("claim_state") != "proposed":
        return blocked("proposed_claim_required")
    if confirmed is not True:
        return blocked("explicit_claim_verification_confirmation_required")
    if not actor:
        return blocked("actor_required")
    if not normalized_sources:
        return blocked("source_record_required")
    if not methodology or not reason:
        return blocked("methodology_and_reason_required")
    if not temporal_reason:
        return blocked("temporal_reason_required")
    if isinstance(temporal_relevance_score, bool):
        return blocked("temporal_relevance_score_invalid")
    try:
        temporal_score = int(temporal_relevance_score)
    except (TypeError, ValueError):
        return blocked("temporal_relevance_score_invalid")
    if temporal_score < 0 or temporal_score > 100:
        return blocked("temporal_relevance_score_invalid")

    case_id = str(claim.get("case_id") or "")
    claim_type = str(claim.get("claim_type") or "")
    identity, error = _identity_component(identity_context, case_id=case_id)
    if error:
        return blocked(error)
    sources, error = _source_components(
        source_ids=normalized_sources,
        case_id=case_id,
        claim_type=claim_type,
    )
    if error:
        return blocked(error)
    linkage, error = _linkage_component(claim_id)
    if error:
        return blocked(error)
    independence = _independence_component(normalized_sources)
    related_conflicts = [
        item
        for item in current_conflicts()
        if claim_id in {item.get("claim_a_id"), item.get("claim_b_id")}
    ]
    unresolved = [
        item for item in related_conflicts if item.get("resolution") == "unresolved"
    ]
    resolved = [
        item for item in related_conflicts if item.get("resolution") != "unresolved"
    ]

    dimensions = {
        "identity_score": int(identity["score"]),
        "source_score": float(sources["source_score"]),
        "directness_score": float(sources["directness_score"]),
        "capture_integrity_score": float(sources["capture_integrity_score"]),
        "temporal_relevance_score": temporal_score,
        "independence_score": int(independence["score"]),
        "linkage_score": int(linkage["score"]),
    }
    weighted = (
        dimensions["source_score"] * 0.20
        + dimensions["directness_score"] * 0.20
        + dimensions["identity_score"] * 0.20
        + dimensions["independence_score"] * 0.15
        + dimensions["capture_integrity_score"] * 0.10
        + dimensions["temporal_relevance_score"] * 0.10
        + dimensions["linkage_score"] * 0.05
    )
    conflict_penalty = min(30, len(unresolved) * 15)
    limitation_penalty = min(20, len(normalized_limitations) * 5)
    support_score = max(
        0,
        min(79, round(weighted - conflict_penalty - limitation_penalty)),
    )
    if support_score < 20:
        band = "insufficient"
    elif support_score < 40:
        band = "limited"
    elif support_score < 60:
        band = "moderate"
    else:
        band = "substantial"

    alternative_group = {
        "case_id": case_id,
        "entity_id": claim.get("entity_id"),
        "claim_type": claim_type,
    }
    alternative_group_id = f"claim-alternative-group-{_sha(alternative_group)[:24]}"
    bindings = {
        "claim_event_sha256": claim.get("claim_event_sha256"),
        "source_bindings_sha256": _sha(sources["bindings"]),
        "identity_context_sha256": _sha(identity),
        "independence_context_sha256": _sha(independence),
        "linkage_context_sha256": _sha(linkage),
        "conflict_event_sha256": [
            item.get("conflict_event_sha256") for item in related_conflicts
        ],
    }
    content = {
        "event_type": ACTION,
        "claim_id": claim_id,
        "case_id": case_id,
        "entity_id": claim.get("entity_id"),
        "claim_type": claim_type,
        "normalized_value": claim.get("normalized_value"),
        "alternative_group_id": alternative_group_id,
        "source_ids": normalized_sources,
        "source_context": sources,
        "identity_context": identity,
        "independence_context": independence,
        "linkage_context": linkage,
        "temporal_reason": temporal_reason,
        "dimensions": dimensions,
        "unresolved_conflict_ids": [item.get("conflict_id") for item in unresolved],
        "resolved_conflict_ids": [item.get("conflict_id") for item in resolved],
        "conflict_penalty": conflict_penalty,
        "limitations": normalized_limitations,
        "limitation_penalty": limitation_penalty,
        "support_score": support_score,
        "confidence_band": band,
        "methodology": methodology,
        "bindings": bindings,
        "bindings_sha256": _sha(bindings),
        "reason": reason,
        "score_cap": 79,
        "score_cap_reason": "human analytic review remains a separate v30.5 gate",
        "truth_assigned": False,
        "human_review_complete": False,
        "dossier_eligible": False,
        "claim_mutated": False,
        "source_mutated": False,
        "dossier_mutated": False,
    }
    digest = _sha(content)
    assessment_id = f"claim-verification-{digest[:24]}"
    if any(
        item.get("claim_verification_assessment_id") == assessment_id
        for item in verification_history(claim_id)
    ):
        return blocked("claim_verification_assessment_already_exists")
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "claim_verification_assessment_id": assessment_id,
        "claim_verification_assessment_sha256": digest,
    }
    result = _record(actor, claim_id, event, ip_address)
    current = find_verification(claim_id)
    return {
        **result,
        "ranking": current.get("ranking") if current else None,
        "status": "claim_verification_assessed",
        "next_action": "human_analytic_review_v30_5",
    }
