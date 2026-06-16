from __future__ import annotations

from typing import Any

from . import database
from .dossier_assembly_workspace_v21_0 import _canonical, _ensure_storage, _json_details, _sha
from .portfolio_operations_dashboard_v24_0 import build_portfolio_operations_dashboard

SCHEMA = "socmint.collaboration_notes_mentions.v26_2"
VERSION = "v26.2.0"
NOTE_ACTION = "case_collaboration_note_created"
CORRECTION_ACTION = "case_collaboration_note_corrected"
MENTION_ACTION = "case_collaboration_mention_created"
ACK_ACTION = "case_collaboration_note_acknowledged"
READ_ACTION = "case_collaboration_update_read"
ACTIONS = (NOTE_ACTION, CORRECTION_ACTION, MENTION_ACTION, ACK_ACTION, READ_ACTION)
TARGET_TYPES = ("case", "evidence", "review", "closure", "archive", "release", "confirmed_link", "relationship_graph")
VISIBILITY_SCOPES = ("case_team", "supervisors", "private")
PRIORITIES = ("low", "normal", "high", "urgent")


def blocked(case_id: str, key: str) -> dict[str, Any]:
    return {"schema": SCHEMA, "version": VERSION, "case_id": case_id, "status": "blocked", "blockers": [{"key": key}], "source_records_mutated": False, "case_access_scope_changed": False, "access_granted_by_mention": False}


def case_state(case_id: str) -> dict[str, Any] | None:
    payload = build_portfolio_operations_dashboard()
    item = next((row for row in payload.get("cases") or [] if str(row.get("case_id") or "") == case_id), None)
    return None if item is None else {"portfolio_schema": payload.get("schema"), "portfolio_version": payload.get("version"), "case": item}


def history(case_id: str) -> list[dict[str, Any]]:
    _ensure_storage()
    session = database.Session()
    try:
        rows = session.query(database.AuditLog).filter(database.AuditLog.target_value == case_id, database.AuditLog.action.in_(ACTIONS)).order_by(database.AuditLog.created_at.asc(), database.AuditLog.id.asc()).all()
        return [{**_json_details(row), "action_record_id": row.id, "recorded_by": row.actor, "recorded_at": row.created_at.isoformat() if row.created_at else None, "source_action": row.action} for row in rows]
    finally:
        session.close()


def _record(case_id: str, actor: str, action: str, event: dict[str, Any], ip_address: str | None) -> tuple[int, str | None]:
    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(actor=actor, action=action, target_value=case_id, ip_address=ip_address, details=_canonical(event))
        session.add(row)
        session.commit()
        session.refresh(row)
        return row.id, row.created_at.isoformat() if row.created_at else None
    finally:
        session.close()


def _record_mentions(case_id: str, note_id: str, note_sha256: str, actor: str, mentions: list[str], visibility: str, priority: str, note_record_id: int, source_state_sha256: str, ip_address: str | None) -> list[dict[str, Any]]:
    result = []
    for user in mentions:
        core = {"case_id": case_id, "event_type": "mention", "collaboration_note_id": note_id, "collaboration_note_sha256": note_sha256, "mentioned_user": user, "mentioned_by": actor, "visibility": visibility, "priority": priority, "status": "unread", "note_action_record_id": note_record_id, "source_case_state_sha256": source_state_sha256}
        digest = _sha(core)
        event = {"schema": SCHEMA, "version": VERSION, **core, "mention_id": f"collaboration-mention-{digest[:24]}", "mention_sha256": digest, "access_granted_by_mention": False, "case_access_scope_changed": False, "source_records_mutated": False}
        record_id, recorded_at = _record(case_id, actor, MENTION_ACTION, event, ip_address)
        result.append({**event, "action_record_id": record_id, "recorded_at": recorded_at})
    return result


def create_note(case_id: str, *, author: str, body: str, target_type: str, target_id: str | None, mentioned_users: list[str] | None, visibility: str, priority: str, confirmed: bool, acknowledgement_required: bool = False, allowed_case_ids: set[str] | None = None, ip_address: str | None = None) -> dict[str, Any]:
    if allowed_case_ids is not None and case_id not in allowed_case_ids: return blocked(case_id, "case_access_required")
    if confirmed is not True: return blocked(case_id, "explicit_collaboration_note_confirmation_required")
    body = str(body or "").strip()
    if not body: return blocked(case_id, "collaboration_note_body_required")
    if target_type not in TARGET_TYPES: return blocked(case_id, "collaboration_note_target_not_in_catalog")
    target_id = str(target_id or "").strip() or None
    if target_type != "case" and not target_id: return blocked(case_id, "collaboration_note_target_id_required")
    if visibility not in VISIBILITY_SCOPES: return blocked(case_id, "collaboration_note_visibility_not_in_catalog")
    if priority not in PRIORITIES: return blocked(case_id, "collaboration_note_priority_not_in_catalog")
    source = case_state(case_id)
    if source is None: return blocked(case_id, "source_case_state_required")
    mentions = sorted({str(v).strip() for v in mentioned_users or [] if str(v).strip() and str(v).strip() != author})
    core = {"case_id": case_id, "event_type": "note", "author": author, "body": body, "target_type": target_type, "target_id": target_id, "mentioned_users": mentions, "visibility": visibility, "priority": priority, "acknowledgement_required": bool(acknowledgement_required), "source_case_state": source, "source_case_state_sha256": _sha(source)}
    digest = _sha(core)
    note_id = f"collaboration-note-{digest[:24]}"
    event = {"schema": SCHEMA, "version": VERSION, **core, "collaboration_note_id": note_id, "collaboration_note_sha256": digest, "collaboration_event_id": f"collaboration-event-{digest[:24]}", "collaboration_event_sha256": digest, "note_status": "active", "source_records_mutated": False, "prior_notes_mutated": False, "case_access_scope_changed": False, "access_granted_by_mention": False}
    record_id, recorded_at = _record(case_id, author, NOTE_ACTION, event, ip_address)
    mention_events = _record_mentions(case_id, note_id, digest, author, mentions, visibility, priority, record_id, core["source_case_state_sha256"], ip_address)
    return {**event, "status": "collaboration_note_recorded", "action_record_id": record_id, "recorded_by": author, "recorded_at": recorded_at, "mention_events": mention_events, "mention_count": len(mention_events), "next_action": "review_collaboration_notes"}


def correct_note(case_id: str, note_id: str, *, author: str, body: str, reason: str, previous_note: dict[str, Any], confirmed: bool, mentioned_users: list[str] | None = None, allowed_case_ids: set[str] | None = None, ip_address: str | None = None) -> dict[str, Any]:
    if allowed_case_ids is not None and case_id not in allowed_case_ids: return blocked(case_id, "case_access_required")
    if confirmed is not True: return blocked(case_id, "explicit_collaboration_note_correction_confirmation_required")
    if previous_note.get("collaboration_note_id") != note_id: return blocked(case_id, "collaboration_note_required")
    if previous_note.get("note_status") != "active": return blocked(case_id, "active_collaboration_note_required")
    body, reason = str(body or "").strip(), str(reason or "").strip()
    if not body: return blocked(case_id, "collaboration_note_body_required")
    if not reason: return blocked(case_id, "collaboration_note_correction_reason_required")
    source = case_state(case_id)
    if source is None: return blocked(case_id, "source_case_state_required")
    mentions = sorted({str(v).strip() for v in (mentioned_users if mentioned_users is not None else previous_note.get("mentioned_users") or []) if str(v).strip() and str(v).strip() != author})
    binding = {"collaboration_note_id": note_id, "collaboration_note_sha256": previous_note.get("collaboration_note_sha256"), "action_record_id": previous_note.get("action_record_id"), "author": previous_note.get("author")}
    core = {"case_id": case_id, "event_type": "correction", "author": author, "body": body, "target_type": previous_note.get("target_type"), "target_id": previous_note.get("target_id"), "mentioned_users": mentions, "visibility": previous_note.get("visibility"), "priority": previous_note.get("priority"), "acknowledgement_required": previous_note.get("acknowledgement_required", False), "reason": reason, "supersedes_note_id": note_id, "supersedes_note_sha256": previous_note.get("collaboration_note_sha256"), "previous_note_binding": binding, "previous_note_binding_sha256": _sha(binding), "source_case_state": source, "source_case_state_sha256": _sha(source)}
    digest = _sha(core)
    corrected_id = f"collaboration-note-{digest[:24]}"
    event = {"schema": SCHEMA, "version": VERSION, **core, "collaboration_note_id": corrected_id, "collaboration_note_sha256": digest, "collaboration_event_id": f"collaboration-correction-{digest[:24]}", "collaboration_event_sha256": digest, "note_status": "active", "source_records_mutated": False, "superseded_note_mutated": False, "case_access_scope_changed": False, "access_granted_by_mention": False}
    record_id, recorded_at = _record(case_id, author, CORRECTION_ACTION, event, ip_address)
    mention_events = _record_mentions(case_id, corrected_id, digest, author, mentions, str(event.get("visibility") or "case_team"), str(event.get("priority") or "normal"), record_id, core["source_case_state_sha256"], ip_address)
    return {**event, "status": "collaboration_note_correction_recorded", "action_record_id": record_id, "recorded_by": author, "recorded_at": recorded_at, "mention_events": mention_events, "mention_count": len(mention_events), "next_action": "review_collaboration_notes"}


def acknowledge_note(case_id: str, note_id: str, *, acknowledged_by: str, response: str | None, note: dict[str, Any], confirmed: bool, allowed_case_ids: set[str] | None = None, ip_address: str | None = None) -> dict[str, Any]:
    if allowed_case_ids is not None and case_id not in allowed_case_ids: return blocked(case_id, "case_access_required")
    if confirmed is not True: return blocked(case_id, "explicit_collaboration_note_acknowledgement_required")
    if note.get("collaboration_note_id") != note_id: return blocked(case_id, "collaboration_note_required")
    if note.get("note_status") != "active": return blocked(case_id, "active_collaboration_note_required")
    binding = {"collaboration_note_id": note_id, "collaboration_note_sha256": note.get("collaboration_note_sha256"), "action_record_id": note.get("action_record_id"), "author": note.get("author")}
    core = {"case_id": case_id, "event_type": "acknowledgement", "collaboration_note_id": note_id, "collaboration_note_sha256": note.get("collaboration_note_sha256"), "acknowledged_by": acknowledged_by, "response": str(response or "").strip() or None, "note_binding": binding, "note_binding_sha256": _sha(binding)}
    digest = _sha(core)
    event = {"schema": SCHEMA, "version": VERSION, **core, "acknowledgement_id": f"collaboration-ack-{digest[:24]}", "collaboration_event_id": f"collaboration-event-{digest[:24]}", "collaboration_event_sha256": digest, "source_records_mutated": False, "note_event_mutated": False, "case_access_scope_changed": False}
    record_id, recorded_at = _record(case_id, acknowledged_by, ACK_ACTION, event, ip_address)
    return {**event, "status": "collaboration_note_acknowledged", "action_record_id": record_id, "recorded_by": acknowledged_by, "recorded_at": recorded_at, "next_action": "review_collaboration_notes"}


def mark_note_read(case_id: str, note_id: str, *, reader: str, note: dict[str, Any], allowed_case_ids: set[str] | None = None, ip_address: str | None = None) -> dict[str, Any]:
    if allowed_case_ids is not None and case_id not in allowed_case_ids: return blocked(case_id, "case_access_required")
    if note.get("collaboration_note_id") != note_id: return blocked(case_id, "collaboration_note_required")
    if note.get("note_status") != "active": return blocked(case_id, "active_collaboration_note_required")
    core = {"case_id": case_id, "event_type": "read", "collaboration_note_id": note_id, "collaboration_note_sha256": note.get("collaboration_note_sha256"), "reader": reader, "status": "read"}
    digest = _sha(core)
    event = {"schema": SCHEMA, "version": VERSION, **core, "read_event_id": f"collaboration-read-{digest[:24]}", "collaboration_event_sha256": digest, "source_records_mutated": False, "note_event_mutated": False, "case_access_scope_changed": False}
    record_id, recorded_at = _record(case_id, reader, READ_ACTION, event, ip_address)
    return {**event, "status": "collaboration_note_marked_read", "action_record_id": record_id, "recorded_by": reader, "recorded_at": recorded_at, "next_action": "review_collaboration_notes"}
