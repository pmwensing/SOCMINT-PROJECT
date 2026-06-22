from __future__ import annotations

from typing import Any

from . import database
from .analytic_dossier_contribution_v30_6 import current_contribution_decisions
from .dossier_assembly_workspace_v21_0 import _canonical, _ensure_storage, _json_details, _sha

SCHEMA = "socmint.publication_candidate.v31_1"
VERSION = "v31.1.0"
ACTION = "publication_candidate_recorded"
STATES = ("proposed", "withdrawn")


def blocked(key: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key}],
        "contribution_mutated": False,
        "draft_revision_created": False,
        "release_approval_performed": False,
        "publication_performed": False,
        "dossier_mutated": False,
    }


def candidate_history() -> list[dict[str, Any]]:
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


def candidates_for_contribution(dossier_contribution_id: str | None = None) -> list[dict[str, Any]]:
    rows = candidate_history()
    if not dossier_contribution_id:
        return rows
    return [
        row
        for row in rows
        if row.get("dossier_contribution_id") == dossier_contribution_id
    ]


def current_publication_candidates() -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    histories: dict[str, list[dict[str, Any]]] = {}
    for item in candidate_history():
        candidate_id = str(item.get("publication_candidate_id") or "")
        if not candidate_id:
            continue
        histories.setdefault(candidate_id, []).append(item)
        latest[candidate_id] = dict(item)
    for candidate_id, item in latest.items():
        item["candidate_history"] = histories.get(candidate_id, [])
    return sorted(latest.values(), key=lambda item: str(item.get("publication_candidate_id")))


def find_candidate(candidate_id: str) -> dict[str, Any] | None:
    for item in current_publication_candidates():
        if item.get("publication_candidate_id") == candidate_id:
            return item
    return None


def _approved_contribution(dossier_contribution_id: str) -> dict[str, Any] | None:
    for item in current_contribution_decisions():
        if (
            item.get("dossier_contribution_id") == dossier_contribution_id
            and item.get("decision") == "approved"
            and item.get("dossier_contribution_authorized") is True
        ):
            return item
    return None


def _record(
    actor: str,
    target_value: str,
    event: dict[str, Any],
    ip_address: str | None,
) -> dict[str, Any]:
    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=actor,
            action=ACTION,
            target_value=target_value,
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


def create_publication_candidate(
    *,
    actor: str,
    dossier_contribution_id: str,
    publication_purpose: str,
    release_scope: str,
    rationale: str,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    dossier_contribution_id = str(dossier_contribution_id or "").strip()
    publication_purpose = str(publication_purpose or "").strip()
    release_scope = str(release_scope or "").strip()
    rationale = str(rationale or "").strip()
    reason = str(reason or "").strip()

    contribution = _approved_contribution(dossier_contribution_id)
    if contribution is None:
        return blocked("approved_v30_dossier_contribution_required")
    if confirmed is not True:
        return blocked("explicit_publication_candidate_confirmation_required")
    if not publication_purpose:
        return blocked("publication_purpose_required")
    if not release_scope:
        return blocked("release_scope_required")
    if not rationale:
        return blocked("publication_candidate_rationale_required")
    if not reason:
        return blocked("administrative_reason_required")

    binding = {
        "dossier_contribution_id": dossier_contribution_id,
        "dossier_contribution_sha256": contribution.get("dossier_contribution_sha256"),
        "claim_id": contribution.get("claim_id"),
        "case_id": contribution.get("case_id"),
        "entity_id": contribution.get("entity_id"),
        "target_section": contribution.get("target_section"),
    }
    content = {
        "event_type": ACTION,
        "candidate_state": "proposed",
        "dossier_contribution_id": dossier_contribution_id,
        "claim_id": contribution.get("claim_id"),
        "case_id": contribution.get("case_id"),
        "entity_id": contribution.get("entity_id"),
        "target_section": contribution.get("target_section"),
        "publication_purpose": publication_purpose,
        "release_scope": release_scope,
        "rationale": rationale,
        "reason": reason,
        "candidate_binding": binding,
        "candidate_binding_sha256": _sha(binding),
        "contribution_mutated": False,
        "draft_revision_created": False,
        "release_approval_performed": False,
        "publication_performed": False,
        "dossier_mutated": False,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "publication_candidate_id": f"publication-candidate-{digest[:24]}",
        "publication_candidate_sha256": digest,
        "supersedes_candidate_event_sha256": None,
    }
    if any(
        item.get("publication_candidate_sha256") == digest
        for item in candidate_history()
    ):
        return blocked("publication_candidate_already_exists")

    result = _record(actor, event["publication_candidate_id"], event, ip_address)
    return {
        **result,
        "status": "publication_candidate_recorded",
        "next_action": "assemble_draft_dossier_revision",
    }


def update_publication_candidate_state(
    *,
    actor: str,
    candidate_id: str,
    candidate_state: str,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    current = find_candidate(candidate_id)
    candidate_state = str(candidate_state or "").strip()
    reason = str(reason or "").strip()
    if current is None:
        return blocked("publication_candidate_required")
    if confirmed is not True:
        return blocked("explicit_publication_candidate_state_confirmation_required")
    if candidate_state not in STATES:
        return blocked("publication_candidate_state_invalid")
    if candidate_state != "withdrawn":
        return blocked("only_withdrawal_state_transition_allowed")
    if current.get("candidate_state") != "proposed":
        return blocked("proposed_publication_candidate_required")
    if not reason:
        return blocked("administrative_reason_required")

    content = {
        key: current.get(key)
        for key in (
            "event_type",
            "dossier_contribution_id",
            "claim_id",
            "case_id",
            "entity_id",
            "target_section",
            "publication_purpose",
            "release_scope",
            "rationale",
            "candidate_binding",
            "candidate_binding_sha256",
        )
    }
    content.update(
        {
            "candidate_state": "withdrawn",
            "reason": reason,
            "contribution_mutated": False,
            "draft_revision_created": False,
            "release_approval_performed": False,
            "publication_performed": False,
            "dossier_mutated": False,
        }
    )
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "publication_candidate_id": candidate_id,
        "publication_candidate_sha256": digest,
        "supersedes_candidate_event_sha256": current.get("publication_candidate_sha256"),
    }
    result = _record(actor, candidate_id, event, ip_address)
    return {
        **result,
        "status": "publication_candidate_state_recorded",
        "next_action": "retain_candidate_history",
    }
