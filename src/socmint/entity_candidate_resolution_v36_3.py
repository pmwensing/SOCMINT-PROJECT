from __future__ import annotations

from typing import Any

from . import database
from .canonical_observation_v36_2 import find_canonical_observation
from .dossier_assembly_workspace_v21_0 import (
    _canonical,
    _ensure_storage,
    _json_details,
    _sha,
)

SCHEMA = "socmint.entity_candidate_resolution.v36_3"
VERSION = "v36.3.0"
ASSESS_ACTION = "entity_candidate_assessed"
DECISION_ACTION = "entity_candidate_decision_recorded"
STRONG_SIGNALS = frozenset(
    {
        "exact_unique_identifier",
        "reciprocal_verified_link",
        "cryptographic_control",
        "exact_registry_identifier",
        "verified_domain_control",
    }
)
SUPPORTING_SIGNALS = frozenset(
    {
        "stable_username_reuse",
        "consistent_biography",
        "location_history",
        "employment_history",
        "linked_account",
        "contact_reuse",
        "archive_continuity",
        "relationship_cluster",
    }
)
WEAK_SIGNALS = frozenset(
    {
        "common_name",
        "avatar_similarity",
        "geographic_proximity",
        "shared_interest",
        "shared_following",
        "tool_probability",
    }
)
NEGATIVE_SIGNALS = frozenset(
    {
        "conflicting_unique_identifier",
        "incompatible_timeline",
        "conflicting_location",
        "distinct_verified_control",
        "explicit_denial",
    }
)
ALL_SIGNALS = STRONG_SIGNALS | SUPPORTING_SIGNALS | WEAK_SIGNALS | NEGATIVE_SIGNALS
DECISIONS = (
    "recommend_merge",
    "keep_separate",
    "insufficient_evidence",
    "needs_revision",
)


def blocked(key: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key}],
        "identity_merged": False,
        "identity_assigned": False,
        "truth_assigned": False,
        "graph_mutated": False,
        "claim_created": False,
        "dossier_mutated": False,
    }


def _history() -> list[dict[str, Any]]:
    _ensure_storage()
    session = database.Session()
    try:
        rows = (
            session.query(database.AuditLog)
            .filter(database.AuditLog.action.in_((ASSESS_ACTION, DECISION_ACTION)))
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
                "source_action": row.action,
                "recorded_at": (
                    row.created_at.isoformat() if row.created_at else None
                ),
            }
            for row in rows
        ]
    finally:
        session.close()


def _record(
    action: str,
    actor: str,
    target: str,
    event: dict[str, Any],
    ip_address: str | None,
) -> dict[str, Any]:
    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=actor,
            action=action,
            target_value=target,
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


def _required(value: Any) -> str:
    return str(value or "").strip()


def assessment_history() -> list[dict[str, Any]]:
    return [
        item for item in _history() if item.get("event_type") == ASSESS_ACTION
    ]


def decision_history(candidate_id: str | None = None) -> list[dict[str, Any]]:
    rows = [
        item for item in _history() if item.get("event_type") == DECISION_ACTION
    ]
    if candidate_id is None:
        return rows
    return [item for item in rows if item.get("candidate_id") == candidate_id]


def current_candidates() -> list[dict[str, Any]]:
    decisions: dict[str, dict[str, Any]] = {}
    for event in decision_history():
        candidate_id = str(event.get("candidate_id") or "")
        if candidate_id:
            decisions[candidate_id] = event
    result = []
    for assessment in assessment_history():
        candidate_id = str(assessment.get("candidate_id") or "")
        result.append(
            {
                **assessment,
                "current_decision": decisions.get(candidate_id),
                "decision_recorded": candidate_id in decisions,
            }
        )
    return sorted(result, key=lambda item: str(item.get("candidate_id") or ""))


def find_candidate(candidate_id: str) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in current_candidates()
            if item.get("candidate_id") == candidate_id
        ),
        None,
    )


def _normalize_signals(
    signals: Any,
    *,
    case_id: str,
) -> tuple[list[dict[str, Any]], str | None]:
    if not isinstance(signals, list) or not signals:
        return [], "entity_resolution_signals_required"
    normalized: list[dict[str, Any]] = []
    for item in signals:
        if not isinstance(item, dict):
            return [], "entity_resolution_signal_invalid"
        signal_type = _required(item.get("signal_type"))
        reason = _required(item.get("reason"))
        observation_ids = item.get("observation_ids")
        if signal_type not in ALL_SIGNALS or not reason:
            return [], "entity_resolution_signal_invalid"
        if not isinstance(observation_ids, list) or not observation_ids:
            return [], "entity_resolution_signal_observations_required"
        unique_ids = sorted(
            {
                _required(observation_id)
                for observation_id in observation_ids
                if _required(observation_id)
            }
        )
        if not unique_ids:
            return [], "entity_resolution_signal_observations_required"
        bindings = []
        for observation_id in unique_ids:
            observation = find_canonical_observation(observation_id)
            if observation is None:
                return [], "accepted_canonical_observation_required"
            if observation.get("observation_state") != "accepted":
                return [], "accepted_canonical_observation_required"
            if str(observation.get("case_id") or "") != case_id:
                return [], "entity_resolution_observation_case_mismatch"
            bindings.append(
                {
                    "canonical_observation_id": observation_id,
                    "canonical_observation_event_sha256": observation.get(
                        "canonical_observation_event_sha256"
                    ),
                    "observation_type": (
                        observation.get("canonical_observation") or {}
                    ).get("observation_type"),
                }
            )
        normalized.append(
            {
                "signal_type": signal_type,
                "signal_class": (
                    "strong"
                    if signal_type in STRONG_SIGNALS
                    else "supporting"
                    if signal_type in SUPPORTING_SIGNALS
                    else "weak"
                    if signal_type in WEAK_SIGNALS
                    else "negative"
                ),
                "reason": reason,
                "observation_bindings": bindings,
                "signal_binding_sha256": _sha(bindings),
            }
        )
    normalized.sort(
        key=lambda item: (
            str(item.get("signal_class") or ""),
            str(item.get("signal_type") or ""),
            str(item.get("signal_binding_sha256") or ""),
        )
    )
    return normalized, None


def _score(signals: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {
        "strong": sum(1 for item in signals if item["signal_class"] == "strong"),
        "supporting": sum(
            1 for item in signals if item["signal_class"] == "supporting"
        ),
        "weak": sum(1 for item in signals if item["signal_class"] == "weak"),
        "negative": sum(
            1 for item in signals if item["signal_class"] == "negative"
        ),
    }
    components = {
        "strong_signal_points": min(75, counts["strong"] * 25),
        "supporting_signal_points": min(24, counts["supporting"] * 8),
        "weak_signal_points": min(10, counts["weak"] * 2),
        "negative_signal_penalty": -min(75, counts["negative"] * 25),
    }
    score = max(0, min(100, sum(components.values())))
    caps = []
    if counts["strong"] == 0:
        score = min(score, 49)
        caps.append("no_strong_signal_cap_49")
    if counts["strong"] == 0 and counts["supporting"] == 0:
        score = min(score, 20)
        caps.append("weak_only_cap_20")
    if counts["negative"]:
        score = min(score, 69)
        caps.append("negative_signal_cap_69")

    if counts["negative"] and score < 40:
        recommendation = "keep_separate"
    elif score >= 70 and counts["strong"] >= 2 and counts["negative"] == 0:
        recommendation = "likely_same_entity"
    elif score >= 40 and counts["negative"] == 0:
        recommendation = "possible_same_entity"
    else:
        recommendation = "insufficient_evidence"
    return {
        "score": score,
        "signal_counts": counts,
        "components": components,
        "caps": caps,
        "recommendation": recommendation,
        "automatic_merge_allowed": False,
    }


def assess_entity_candidate(
    *,
    actor: str,
    case_id: str,
    entity_a_id: str,
    entity_b_id: str,
    signals: list[dict[str, Any]] | None,
    limitations: list[str] | None,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    actor = _required(actor)
    case_id = _required(case_id)
    entity_a_id = _required(entity_a_id)
    entity_b_id = _required(entity_b_id)
    reason = _required(reason)
    limitations = sorted(
        {
            _required(item)
            for item in (limitations or [])
            if _required(item)
        }
    )
    if confirmed is not True:
        return blocked("explicit_entity_candidate_assessment_confirmation_required")
    if not actor:
        return blocked("actor_required")
    if not case_id:
        return blocked("case_id_required")
    if not entity_a_id or not entity_b_id:
        return blocked("candidate_entity_ids_required")
    if entity_a_id == entity_b_id:
        return blocked("candidate_entities_must_be_distinct")
    if not reason:
        return blocked("administrative_reason_required")

    normalized_signals, error = _normalize_signals(signals, case_id=case_id)
    if error:
        return blocked(error)
    scoring = _score(normalized_signals)
    ordered_entities = sorted((entity_a_id, entity_b_id))
    identity = {
        "case_id": case_id,
        "entity_ids": ordered_entities,
        "signal_bindings": [
            item["signal_binding_sha256"] for item in normalized_signals
        ],
        "limitations": limitations,
    }
    candidate_id = f"entity-candidate-{_sha(identity)[:24]}"
    if find_candidate(candidate_id) is not None:
        return blocked("entity_candidate_assessment_already_exists")

    content = {
        "event_type": ASSESS_ACTION,
        "candidate_id": candidate_id,
        "case_id": case_id,
        "entity_a_id": ordered_entities[0],
        "entity_b_id": ordered_entities[1],
        "signals": normalized_signals,
        "signal_manifest_sha256": _sha(normalized_signals),
        "limitations": limitations,
        "scoring": scoring,
        "reason": reason,
        "identity_merged": False,
        "identity_assigned": False,
        "truth_assigned": False,
        "graph_mutated": False,
        "claim_created": False,
        "dossier_mutated": False,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "entity_candidate_assessment_id": (
            f"entity-candidate-assessment-{digest[:24]}"
        ),
        "entity_candidate_assessment_sha256": digest,
    }
    result = _record(ASSESS_ACTION, actor, candidate_id, event, ip_address)
    return {
        **result,
        "status": "entity_candidate_assessed",
        "next_action": "human_entity_candidate_decision",
    }


def record_entity_candidate_decision(
    *,
    actor: str,
    candidate_id: str,
    decision: str,
    rationale: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    actor = _required(actor)
    candidate_id = _required(candidate_id)
    decision = _required(decision)
    rationale = _required(rationale)
    candidate = find_candidate(candidate_id)
    if candidate is None:
        return blocked("entity_candidate_required")
    if confirmed is not True:
        return blocked("explicit_entity_candidate_decision_confirmation_required")
    if not actor:
        return blocked("actor_required")
    if decision not in DECISIONS:
        return blocked("entity_candidate_decision_invalid")
    if not rationale:
        return blocked("decision_rationale_required")
    if candidate.get("decision_recorded") is True:
        return blocked("entity_candidate_decision_already_recorded")
    recommendation = (candidate.get("scoring") or {}).get("recommendation")
    if decision == "recommend_merge" and recommendation != "likely_same_entity":
        return blocked("merge_recommendation_requires_likely_same_entity")

    content = {
        "event_type": DECISION_ACTION,
        "candidate_id": candidate_id,
        "case_id": candidate.get("case_id"),
        "decision": decision,
        "rationale": rationale,
        "assessment_sha256": candidate.get(
            "entity_candidate_assessment_sha256"
        ),
        "scoring_recommendation": recommendation,
        "identity_merged": False,
        "identity_assigned": False,
        "truth_assigned": False,
        "graph_mutated": False,
        "claim_created": False,
        "dossier_mutated": False,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "entity_candidate_decision_id": (
            f"entity-candidate-decision-{digest[:24]}"
        ),
        "entity_candidate_decision_sha256": digest,
    }
    result = _record(DECISION_ACTION, actor, candidate_id, event, ip_address)
    return {
        **result,
        "status": "entity_candidate_decision_recorded",
        "next_action": "retain_reviewed_candidate_without_graph_mutation",
    }
