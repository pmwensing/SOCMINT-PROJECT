from __future__ import annotations

from typing import Any

from . import database
from .dossier_assembly_workspace_v21_0 import _canonical, _ensure_storage, _json_details, _sha
from .immutable_published_revision_v31_5 import current_published_revisions

SCHEMA = "socmint.publication_supersession.v31_6"
VERSION = "v31.6.0"
ACTION = "published_revision_supersession_recorded"


def blocked(key: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key}],
        "predecessor_mutated": False,
        "successor_mutated": False,
        "published_history_deleted": False,
        "external_transmission_performed": False,
    }


def supersession_history() -> list[dict[str, Any]]:
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
                "supersession_record_id": row.id,
                "actor": row.actor,
                "recorded_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    finally:
        session.close()


def find_published_revision(revision_id: str) -> dict[str, Any] | None:
    for item in current_published_revisions():
        if item.get("published_revision_id") == revision_id:
            return item
    return None


def revision_history_for_case(case_id: str | None = None) -> dict[str, Any]:
    revisions = [
        item
        for item in current_published_revisions()
        if not case_id or item.get("case_id") == case_id
    ]
    revision_ids = {str(item.get("published_revision_id") or "") for item in revisions}
    links = [
        item
        for item in supersession_history()
        if item.get("predecessor_revision_id") in revision_ids
        or item.get("successor_revision_id") in revision_ids
    ]
    predecessor_to_successor = {
        str(item.get("predecessor_revision_id")): str(item.get("successor_revision_id"))
        for item in links
    }
    successor_to_predecessor = {
        str(item.get("successor_revision_id")): str(item.get("predecessor_revision_id"))
        for item in links
    }
    history = []
    for item in revisions:
        revision_id = str(item.get("published_revision_id") or "")
        history.append(
            {
                **item,
                "revision_status": "superseded" if revision_id in predecessor_to_successor else "active",
                "superseded_by_revision_id": predecessor_to_successor.get(revision_id),
                "supersedes_revision_id": successor_to_predecessor.get(revision_id),
            }
        )
    return {
        "schema": "socmint.publication_revision_history.v31_6",
        "version": VERSION,
        "case_id": case_id,
        "revisions": history,
        "revision_count": len(history),
        "supersession_links": links,
        "supersession_count": len(links),
        "active_revision_ids": [
            item["published_revision_id"]
            for item in history
            if item["revision_status"] == "active"
        ],
    }


def _record(actor: str, target_value: str, event: dict[str, Any], ip_address: str | None) -> dict[str, Any]:
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
            "supersession_record_id": row.id,
            "actor": actor,
            "recorded_at": row.created_at.isoformat() if row.created_at else None,
        }
    finally:
        session.close()


def record_publication_supersession(
    *,
    actor: str,
    predecessor_revision_id: str,
    successor_revision_id: str,
    reason: str,
    note: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    predecessor_revision_id = str(predecessor_revision_id or "").strip()
    successor_revision_id = str(successor_revision_id or "").strip()
    reason = str(reason or "").strip()
    note = str(note or "").strip()

    predecessor = find_published_revision(predecessor_revision_id)
    successor = find_published_revision(successor_revision_id)
    if predecessor is None:
        return blocked("predecessor_published_revision_required")
    if successor is None:
        return blocked("successor_published_revision_required")
    if predecessor_revision_id == successor_revision_id:
        return blocked("distinct_published_revisions_required")
    if predecessor.get("case_id") != successor.get("case_id"):
        return blocked("same_case_revision_history_required")
    if confirmed is not True:
        return blocked("explicit_supersession_confirmation_required")
    if not reason:
        return blocked("administrative_reason_required")

    links = supersession_history()
    if any(item.get("predecessor_revision_id") == predecessor_revision_id for item in links):
        return blocked("predecessor_already_superseded")
    if any(item.get("successor_revision_id") == successor_revision_id for item in links):
        return blocked("successor_already_has_predecessor")

    binding = {
        "predecessor_revision_id": predecessor_revision_id,
        "predecessor_revision_sha256": predecessor.get("published_revision_sha256"),
        "successor_revision_id": successor_revision_id,
        "successor_revision_sha256": successor.get("published_revision_sha256"),
        "case_id": predecessor.get("case_id"),
    }
    content = {
        "event_type": ACTION,
        "case_id": predecessor.get("case_id"),
        "predecessor_revision_id": predecessor_revision_id,
        "predecessor_revision_sha256": predecessor.get("published_revision_sha256"),
        "successor_revision_id": successor_revision_id,
        "successor_revision_sha256": successor.get("published_revision_sha256"),
        "reason": reason,
        "note": note,
        "supersession_binding": binding,
        "supersession_binding_sha256": _sha(binding),
        "predecessor_mutated": False,
        "successor_mutated": False,
        "published_history_deleted": False,
        "external_transmission_performed": False,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "supersession_id": f"published-revision-supersession-{digest[:24]}",
        "supersession_sha256": digest,
    }
    if any(item.get("supersession_sha256") == digest for item in links):
        return blocked("supersession_already_exists")

    result = _record(actor, event["supersession_id"], event, ip_address)
    return {
        **result,
        "status": "supersession_recorded",
        "next_action": "review_publication_revision_history",
    }
