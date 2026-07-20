from __future__ import annotations

from typing import Any

from . import database
from .case_import_pilot_v37_3 import (
    find_review_decision,
    find_scope_assessment,
)
from .dossier_assembly_workspace_v21_0 import (
    _canonical,
    _ensure_storage,
    _json_details,
    _sha,
)
from .evidence_ingestion_v29_4 import derive_observation
from .operational_import_record_projection_v37_2 import (
    find_staged_record_projection,
)
from .operational_import_v37_1 import find_import

SCHEMA = "socmint.import_observation_promotion.v37_4"
VERSION = "v37.4.0"
ACTION = "reviewed_import_record_promoted"


def blocked(key: str, upstream: dict[str, Any] | None = None) -> dict[str, Any]:
    result = {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key}],
        "bulk_promotion_performed": False,
        "automatic_promotion_performed": False,
        "truth_assigned": False,
        "entity_merged": False,
        "claim_approved": False,
        "dossier_mutated": False,
        "export_created": False,
        "published": False,
    }
    if upstream is not None:
        result["upstream_result"] = upstream
    return result


def _required(value: Any) -> str:
    return str(value or "").strip()


def _history() -> list[dict[str, Any]]:
    _ensure_storage()
    session = database.Session()
    try:
        rows = (
            session.query(database.AuditLog)
            .filter_by(action=ACTION)
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
    promotion_id: str,
    event: dict[str, Any],
    ip_address: str | None,
) -> dict[str, Any]:
    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=actor,
            action=ACTION,
            target_value=promotion_id,
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


def current_promotions() -> list[dict[str, Any]]:
    current: dict[str, dict[str, Any]] = {}
    for event in _history():
        staged_record_id = str(event.get("staged_record_id") or "")
        if staged_record_id:
            current[staged_record_id] = event
    return sorted(
        current.values(),
        key=lambda item: str(item.get("staged_record_id") or ""),
    )


def find_promotion(staged_record_id: str) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in current_promotions()
            if item.get("staged_record_id") == staged_record_id
        ),
        None,
    )


def promote_reviewed_record(
    *,
    actor: str,
    staged_record_id: str,
    derivation_method: str,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    actor = _required(actor)
    staged_record_id = _required(staged_record_id)
    derivation_method = _required(derivation_method)
    reason = _required(reason)
    if confirmed is not True:
        return blocked("explicit_single_record_promotion_confirmation_required")
    if not actor:
        return blocked("actor_required")
    if not staged_record_id:
        return blocked("staged_record_id_required")
    if not derivation_method or not reason:
        return blocked("derivation_method_and_reason_required")

    existing = find_promotion(staged_record_id)
    if existing is not None:
        return {
            **existing,
            "status": "reviewed_import_record_promotion_reused",
            "idempotent_replay": True,
            "next_action": "register_canonical_observation_envelope",
        }

    staged = find_staged_record_projection(staged_record_id)
    review = find_review_decision(staged_record_id)
    assessment = find_scope_assessment(staged_record_id)
    if staged is None or review is None or assessment is None:
        return blocked("staged_record_scope_and_review_required")
    if review.get("decision") != "accepted":
        return blocked("accepted_import_review_decision_required")
    if review.get("observation_promotion_allowed") is not True:
        return blocked("observation_promotion_not_authorized")
    if staged.get("initial_state") == "duplicate":
        return blocked("duplicate_record_cannot_be_promoted")
    if assessment.get("scope_status") == "out_of_scope":
        return blocked("out_of_scope_record_cannot_be_promoted")

    import_id = _required(staged.get("operational_import_id"))
    parent = find_import(import_id)
    if parent is None:
        return blocked("operational_import_required")
    envelope = parent.get("envelope") or {}
    artifact_binding = envelope.get("artifact_binding") or {}
    if not isinstance(artifact_binding, dict):
        return blocked("import_artifact_binding_required")
    artifact_id = _required(artifact_binding.get("artifact_id"))
    if not artifact_id:
        return blocked("import_artifact_binding_required")

    upstream = derive_observation(
        actor=actor,
        artifact_id=artifact_id,
        observation_type=_required(staged.get("record_type")),
        normalized_value=staged.get("normalized_value"),
        confidence=str(staged.get("extraction_confidence") or "0.5"),
        derivation_method=derivation_method,
        reason=reason,
        confirmed=True,
        ip_address=ip_address,
    )
    if upstream.get("status") != "evidence_observation_derived":
        return blocked("authoritative_observation_derivation_failed", upstream)

    binding = {
        "operational_import_id": import_id,
        "import_event_sha256": parent.get("operational_import_event_sha256"),
        "staged_record_id": staged_record_id,
        "record_sha256": staged.get("record_sha256"),
        "scope_assessment_id": assessment.get("scope_assessment_id"),
        "scope_event_sha256": assessment.get("scope_event_sha256"),
        "review_decision_id": review.get("review_decision_id"),
        "review_decision_sha256": review.get("review_decision_sha256"),
        "artifact_id": artifact_id,
        "observation_id": upstream.get("observation_id"),
        "observation_sha256": upstream.get("observation_sha256"),
        "artifact_event_sha256": upstream.get("artifact_event_sha256"),
    }
    promotion_id = f"import-observation-promotion-{_sha(binding)[:24]}"
    content = {
        "event_type": ACTION,
        "promotion_id": promotion_id,
        "case_id": envelope.get("case_id"),
        "staged_record_id": staged_record_id,
        "binding": binding,
        "binding_sha256": _sha(binding),
        "relocation_context_only": review.get("relocation_context_only") is True,
        "issue_claim_support_allowed": review.get("issue_claim_support_allowed") is True,
        "reason": reason,
        "bulk_promotion_performed": False,
        "automatic_promotion_performed": False,
        "truth_assigned": False,
        "entity_merged": False,
        "claim_approved": False,
        "dossier_mutated": False,
        "export_created": False,
        "published": False,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "promotion_event_id": f"import-observation-promotion-event-{digest[:24]}",
        "promotion_event_sha256": digest,
    }
    result = _record(actor, promotion_id, event, ip_address)
    return {
        **result,
        "status": "reviewed_import_record_promoted",
        "idempotent_replay": False,
        "next_action": "register_canonical_observation_envelope",
    }
