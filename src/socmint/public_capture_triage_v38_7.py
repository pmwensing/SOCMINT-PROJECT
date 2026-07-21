from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from . import database
from .dossier_assembly_workspace_v21_0 import (
    _canonical,
    _ensure_storage,
    _json_details,
    _sha,
)
from .operational_import_v37_1 import register_import_envelope
from .source_independence_v36_4 import (
    assess_source_independence,
    groups_for_sources,
)
from .source_registry_v36_1 import find_source

SCHEMA = "socmint.public_capture_triage.v38_7"
VERSION = "v38.7.0"
TRIAGE_ACTION = "public_capture_triage_recorded"
RELEVANCE_CLASSES = {
    "direct_case",
    "relocation_mitigation",
    "candidate_review",
    "out_of_scope",
}


def _required(value: Any) -> str:
    return str(value or "").strip()


def _strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted({_required(item) for item in value if _required(item)})


def _time(value: Any) -> str | None:
    raw = _required(value)
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc).isoformat()


def blocked(key: str, **details: Any) -> dict[str, Any]:
    result = {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key}],
        "source_mutated": False,
        "artifact_mutated": False,
        "independence_assessed": False,
        "import_registered": False,
        "import_records_staged": False,
        "observation_created": False,
        "truth_assigned": False,
        "entity_merged": False,
        "claim_approved": False,
        "dossier_mutated": False,
        "export_created": False,
        "published": False,
    }
    if details:
        result["details"] = details
    return result


def _history() -> list[dict[str, Any]]:
    _ensure_storage()
    session = database.Session()
    try:
        rows = (
            session.query(database.AuditLog)
            .filter_by(action=TRIAGE_ACTION)
            .order_by(database.AuditLog.created_at.asc(), database.AuditLog.id.asc())
            .all()
        )
        return [
            {
                **_json_details(row),
                "audit_record_id": row.id,
                "actor": row.actor,
                "recorded_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    finally:
        session.close()


def _record(
    actor: str,
    triage_id: str,
    event: dict[str, Any],
    ip_address: str | None,
) -> dict[str, Any]:
    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=actor,
            action=TRIAGE_ACTION,
            target_value=triage_id,
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
            "recorded_at": row.created_at.isoformat() if row.created_at else None,
        }
    finally:
        session.close()


def current_triage_records() -> list[dict[str, Any]]:
    current: dict[str, dict[str, Any]] = {}
    for event in _history():
        triage_id = _required(event.get("capture_triage_id"))
        if triage_id:
            current[triage_id] = event
    return sorted(
        current.values(),
        key=lambda item: str(item.get("recorded_at") or ""),
        reverse=True,
    )


def find_triage(capture_triage_id: str) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in current_triage_records()
            if item.get("capture_triage_id") == capture_triage_id
        ),
        None,
    )


def _normalize_relevance(
    relevance_assessments: Any,
    source_ids: list[str],
) -> tuple[dict[str, dict[str, Any]] | None, str | None]:
    if not isinstance(relevance_assessments, list):
        return None, "source_relevance_assessments_required"
    normalized: dict[str, dict[str, Any]] = {}
    for item in relevance_assessments:
        if not isinstance(item, dict):
            return None, "source_relevance_assessment_invalid"
        source_id = _required(item.get("source_id"))
        classification = _required(item.get("classification"))
        rationale = _required(item.get("rationale"))
        matched_terms = _strings(item.get("matched_terms"))
        matched_entities = _strings(item.get("matched_entities"))
        limitations = _strings(item.get("limitations"))
        if source_id not in source_ids or source_id in normalized:
            return None, "source_relevance_assessment_invalid"
        if classification not in RELEVANCE_CLASSES or not rationale:
            return None, "source_relevance_assessment_invalid"
        if classification == "direct_case" and not (
            matched_terms or matched_entities
        ):
            return None, "direct_case_relevance_evidence_required"
        normalized[source_id] = {
            "source_id": source_id,
            "classification": classification,
            "rationale": rationale,
            "matched_terms": matched_terms,
            "matched_entities": matched_entities,
            "limitations": limitations,
        }
    if set(normalized) != set(source_ids):
        return None, "complete_source_relevance_assessments_required"
    return normalized, None


def _source_projection(source: dict[str, Any]) -> dict[str, Any]:
    capture = source.get("capture") or {}
    artifact = capture.get("artifact_binding") or {}
    return {
        "source_id": source.get("source_id"),
        "source_event_sha256": source.get("source_event_sha256"),
        "case_id": source.get("case_id"),
        "source_type": source.get("source_type"),
        "publisher_or_operator": source.get("publisher_or_operator"),
        "original_or_derived": source.get("original_or_derived"),
        "canonical_url": capture.get("canonical_url"),
        "retrieved_url": capture.get("retrieved_url"),
        "captured_at": capture.get("captured_at"),
        "content_sha256": capture.get("content_sha256"),
        "capture_sha256": source.get("capture_sha256"),
        "capture_artifact_id": capture.get("capture_artifact_id"),
        "artifact_event_sha256": artifact.get("artifact_event_sha256"),
        "adapter_name": capture.get("adapter_name"),
        "adapter_version": capture.get("adapter_version"),
    }


def triage_public_captures(
    *,
    actor: str,
    case_id: str,
    source_ids: list[str] | None,
    relevance_assessments: list[dict[str, Any]] | None,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    actor = _required(actor)
    case_id = _required(case_id)
    reason = _required(reason)
    normalized_ids = sorted(
        {_required(item) for item in (source_ids or []) if _required(item)}
    )
    if confirmed is not True:
        return blocked("explicit_capture_triage_confirmation_required")
    if not actor:
        return blocked("actor_required")
    if not case_id:
        return blocked("case_id_required")
    if not normalized_ids:
        return blocked("at_least_one_source_required")
    if not reason:
        return blocked("administrative_reason_required")

    relevance, relevance_error = _normalize_relevance(
        relevance_assessments,
        normalized_ids,
    )
    if relevance_error:
        return blocked(relevance_error)
    assert relevance is not None

    sources = []
    for source_id in normalized_ids:
        source = find_source(source_id)
        if source is None:
            return blocked("registered_source_required", source_id=source_id)
        if _required(source.get("case_id")) != case_id:
            return blocked("capture_triage_case_mismatch", source_id=source_id)
        capture = source.get("capture") or {}
        artifact = capture.get("artifact_binding") or {}
        if not all(
            (
                _required(capture.get("content_sha256")),
                _required(capture.get("canonical_url")),
                _time(capture.get("captured_at")),
                _required(capture.get("capture_artifact_id")),
                _required(artifact.get("artifact_event_sha256")),
            )
        ):
            return blocked("complete_registered_capture_binding_required")
        sources.append(_source_projection(source))

    by_hash: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_canonical: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for source in sources:
        by_hash[str(source["content_sha256"])].append(source)
        by_canonical[str(source["canonical_url"])].append(source)

    duplicate_groups = []
    duplicate_secondary_ids: set[str] = set()
    mirror_proposals = []
    for content_sha256, members in sorted(by_hash.items()):
        if len(members) < 2:
            continue
        ordered = sorted(
            members,
            key=lambda item: (
                str(item.get("captured_at") or ""),
                str(item.get("source_id") or ""),
            ),
        )
        primary = str(ordered[0]["source_id"])
        secondary = [str(item["source_id"]) for item in ordered[1:]]
        duplicate_secondary_ids.update(secondary)
        identity = {
            "case_id": case_id,
            "content_sha256": content_sha256,
            "source_ids": [str(item["source_id"]) for item in ordered],
        }
        group_id = f"capture-duplicate-group-{_sha(identity)[:24]}"
        duplicate_groups.append(
            {
                "duplicate_group_id": group_id,
                "content_sha256": content_sha256,
                "source_ids": identity["source_ids"],
                "primary_source_id": primary,
                "support_suppressed_source_ids": secondary,
                "deterministic_primary_suggestion_only": True,
            }
        )
        proposal = {
            "relationship": "mirror",
            "source_ids": identity["source_ids"],
            "signals": [
                {
                    "signal_type": "exact_content_hash",
                    "reason": "Registered captures share the exact content SHA-256.",
                }
            ],
            "limitations": [
                "Exact content identity supports a mirror proposal but does not prove publication origin or intent."
            ],
        }
        mirror_proposals.append(
            {
                **proposal,
                "mirror_proposal_id": f"capture-mirror-proposal-{_sha(proposal)[:24]}",
                "requires_explicit_v36_4_confirmation": True,
            }
        )

    recapture_groups = []
    change_summaries = []
    for canonical_url, members in sorted(by_canonical.items()):
        if len(members) < 2:
            continue
        ordered = sorted(
            members,
            key=lambda item: (
                str(item.get("captured_at") or ""),
                str(item.get("source_id") or ""),
            ),
        )
        source_order = [str(item["source_id"]) for item in ordered]
        recapture_identity = {
            "case_id": case_id,
            "canonical_url": canonical_url,
            "source_ids": source_order,
        }
        recapture_groups.append(
            {
                "recapture_group_id": f"capture-recapture-group-{_sha(recapture_identity)[:24]}",
                "canonical_url": canonical_url,
                "source_ids": source_order,
                "capture_count": len(ordered),
                "distinct_content_hash_count": len(
                    {str(item["content_sha256"]) for item in ordered}
                ),
            }
        )
        for previous, current in zip(ordered, ordered[1:]):
            unchanged = previous["content_sha256"] == current["content_sha256"]
            summary = {
                "canonical_url": canonical_url,
                "previous_source_id": previous["source_id"],
                "current_source_id": current["source_id"],
                "previous_captured_at": previous["captured_at"],
                "current_captured_at": current["captured_at"],
                "previous_content_sha256": previous["content_sha256"],
                "current_content_sha256": current["content_sha256"],
                "change_state": "unchanged" if unchanged else "content_hash_changed",
                "factual_significance_assigned": False,
                "causation_assigned": False,
            }
            change_summaries.append(
                {
                    **summary,
                    "change_summary_id": f"capture-change-summary-{_sha(summary)[:24]}",
                }
            )

    source_triage = []
    for source in sorted(sources, key=lambda item: str(item["source_id"])):
        source_id = str(source["source_id"])
        assessment = relevance[source_id]
        duplicate_secondary = source_id in duplicate_secondary_ids
        classification = assessment["classification"]
        relevance_eligible = classification in {
            "direct_case",
            "relocation_mitigation",
        }
        support_eligible = relevance_eligible and not duplicate_secondary
        source_triage.append(
            {
                **source,
                "relevance": assessment,
                "duplicate_secondary": duplicate_secondary,
                "support_eligible": support_eligible,
                "v37_handoff_eligible": support_eligible,
                "review_required": classification == "candidate_review",
                "out_of_scope": classification == "out_of_scope",
                "observation_created": False,
                "truth_assigned": False,
            }
        )

    existing_groups = groups_for_sources(normalized_ids)
    content = {
        "event_type": TRIAGE_ACTION,
        "case_id": case_id,
        "source_ids": normalized_ids,
        "source_bindings": sources,
        "source_bindings_sha256": _sha(sources),
        "source_triage": source_triage,
        "source_triage_sha256": _sha(source_triage),
        "duplicate_groups": duplicate_groups,
        "mirror_proposals": mirror_proposals,
        "recapture_groups": recapture_groups,
        "change_summaries": change_summaries,
        "existing_independence_group_ids": sorted(
            {
                _required(item.get("independence_group_id"))
                for item in existing_groups
                if _required(item.get("independence_group_id"))
            }
        ),
        "counts": {
            "sources": len(sources),
            "support_eligible": sum(
                1 for item in source_triage if item["support_eligible"]
            ),
            "duplicate_groups": len(duplicate_groups),
            "mirror_proposals": len(mirror_proposals),
            "recapture_groups": len(recapture_groups),
            "change_summaries": len(change_summaries),
            "candidate_review": sum(
                1
                for item in source_triage
                if item["relevance"]["classification"] == "candidate_review"
            ),
            "out_of_scope": sum(
                1
                for item in source_triage
                if item["relevance"]["classification"] == "out_of_scope"
            ),
        },
        "reason": reason,
        "source_mutated": False,
        "artifact_mutated": False,
        "independence_assessed": False,
        "import_registered": False,
        "import_records_staged": False,
        "observation_created": False,
        "truth_assigned": False,
        "entity_merged": False,
        "claim_approved": False,
        "dossier_mutated": False,
        "export_created": False,
        "published": False,
    }
    digest = _sha(content)
    triage_id = f"public-capture-triage-{digest[:24]}"
    existing = find_triage(triage_id)
    if existing is not None:
        return {
            **existing,
            "status": "public_capture_triage_reused",
            "idempotent_replay": True,
            "next_action": "review_capture_triage",
        }
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "capture_triage_id": triage_id,
        "capture_triage_sha256": digest,
    }
    result = _record(actor, triage_id, event, ip_address)
    return {
        **result,
        "status": "public_capture_triage_recorded",
        "idempotent_replay": False,
        "next_action": "review_capture_triage",
    }


def confirm_mirror_proposal(
    *,
    actor: str,
    capture_triage_id: str,
    mirror_proposal_id: str,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    if confirmed is not True:
        return blocked("explicit_mirror_assessment_confirmation_required")
    actor = _required(actor)
    reason = _required(reason)
    if not actor:
        return blocked("actor_required")
    if not reason:
        return blocked("administrative_reason_required")
    triage = find_triage(_required(capture_triage_id))
    if triage is None:
        return blocked("capture_triage_record_required")
    proposal = next(
        (
            item
            for item in triage.get("mirror_proposals") or []
            if item.get("mirror_proposal_id") == _required(mirror_proposal_id)
        ),
        None,
    )
    if proposal is None:
        return blocked("mirror_proposal_required")
    result = assess_source_independence(
        actor=actor,
        case_id=str(triage.get("case_id") or ""),
        source_ids=list(proposal.get("source_ids") or []),
        relationship="mirror",
        signals=list(proposal.get("signals") or []),
        limitations=list(proposal.get("limitations") or []),
        reason=reason,
        confirmed=True,
        ip_address=ip_address,
    )
    if result.get("status") != "source_independence_assessed":
        return {
            **blocked("v36_4_mirror_assessment_failed", result=result),
            "independence_assessed": False,
        }
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "capture_mirror_proposal_confirmed",
        "capture_triage_id": triage.get("capture_triage_id"),
        "capture_triage_sha256": triage.get("capture_triage_sha256"),
        "mirror_proposal_id": proposal.get("mirror_proposal_id"),
        "source_independence_assessment": result,
        "independence_assessed": True,
        "source_mutated": False,
        "artifact_mutated": False,
        "import_registered": False,
        "observation_created": False,
        "truth_assigned": False,
        "claim_approved": False,
        "dossier_mutated": False,
    }


def handoff_capture_to_v37(
    *,
    actor: str,
    capture_triage_id: str,
    source_id: str,
    original_filename: str,
    media_type: str,
    export_format: str,
    imported_at: str,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    if confirmed is not True:
        return blocked("explicit_v37_handoff_confirmation_required")
    actor = _required(actor)
    reason = _required(reason)
    if not actor:
        return blocked("actor_required")
    if not reason:
        return blocked("administrative_reason_required")
    triage = find_triage(_required(capture_triage_id))
    if triage is None:
        return blocked("capture_triage_record_required")
    selected = next(
        (
            item
            for item in triage.get("source_triage") or []
            if item.get("source_id") == _required(source_id)
        ),
        None,
    )
    if selected is None:
        return blocked("triaged_source_required")
    if selected.get("v37_handoff_eligible") is not True:
        return blocked("triaged_source_not_eligible_for_v37_handoff")
    artifact_id = _required(selected.get("capture_artifact_id"))
    content_sha256 = _required(selected.get("content_sha256"))
    captured_at = _time(selected.get("captured_at"))
    imported = _time(imported_at)
    if not artifact_id or not content_sha256 or captured_at is None:
        return blocked("complete_capture_artifact_binding_required")
    if imported is None:
        return blocked("imported_at_invalid")

    result = register_import_envelope(
        actor=actor,
        case_id=str(triage.get("case_id") or ""),
        purpose="Review a selected public-web capture from v38.7 triage.",
        artifact_id=artifact_id,
        content_sha256=content_sha256,
        original_filename=original_filename,
        media_type=media_type,
        export_format=export_format,
        tool_name="SOCMINT Public Capture Triage",
        tool_version=VERSION,
        adapter_name=_required(selected.get("adapter_name")) or "public-web-capture",
        adapter_version=_required(selected.get("adapter_version")) or VERSION,
        exported_at=captured_at,
        imported_at=imported,
        declared_record_count=1,
        source_references=[
            _required(selected.get("canonical_url")),
            _required(selected.get("retrieved_url")),
        ],
        collection_context={
            "public_capture_triage": True,
            "capture_triage_id": triage.get("capture_triage_id"),
            "capture_triage_sha256": triage.get("capture_triage_sha256"),
            "source_id": selected.get("source_id"),
            "relevance": selected.get("relevance"),
            "duplicate_secondary": selected.get("duplicate_secondary"),
            "operator_selected": True,
        },
        reason=reason,
        confirmed=True,
        ip_address=ip_address,
    )
    if result.get("status") not in {
        "operational_import_registered",
        "operational_import_reused",
    }:
        return {
            **blocked("v37_import_handoff_failed", result=result),
            "import_registered": False,
        }
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "public_capture_handed_off_to_v37",
        "capture_triage_id": triage.get("capture_triage_id"),
        "capture_triage_sha256": triage.get("capture_triage_sha256"),
        "source_id": selected.get("source_id"),
        "operational_import": result,
        "import_registered": True,
        "import_records_staged": False,
        "observation_created": False,
        "truth_assigned": False,
        "entity_merged": False,
        "claim_approved": False,
        "dossier_mutated": False,
        "export_created": False,
        "published": False,
        "next_action": "stage_import_records_separately_after_review",
    }
