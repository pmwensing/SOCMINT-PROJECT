from __future__ import annotations

from collections import defaultdict
from typing import Any

from .collaboration_note_events_v26_2 import PRIORITIES, TARGET_TYPES, VISIBILITY_SCOPES, history


def current_notes(case_id: str) -> list[dict[str, Any]]:
    notes: dict[str, dict[str, Any]] = {}
    superseded: dict[str, str] = {}
    acknowledgements: dict[str, list[dict[str, Any]]] = defaultdict(list)
    reads: dict[str, set[str]] = defaultdict(set)
    for event in history(case_id):
        kind = event.get("event_type")
        note_id = str(event.get("collaboration_note_id") or "")
        if kind in {"note", "correction"} and note_id:
            notes[note_id] = {**event, "note_status": "active"}
            previous = str(event.get("supersedes_note_id") or "")
            if previous:
                superseded[previous] = note_id
        elif kind == "acknowledgement" and note_id:
            acknowledgements[note_id].append(event)
        elif kind == "read" and note_id:
            reader = str(event.get("reader") or event.get("recorded_by") or "")
            if reader:
                reads[note_id].add(reader)
    for previous, replacement in superseded.items():
        if previous in notes:
            notes[previous] = {**notes[previous], "note_status": "superseded", "superseded_by_note_id": replacement}
    result = []
    for note_id, item in notes.items():
        acks = acknowledgements.get(note_id, [])
        result.append({**item, "acknowledgements": acks, "acknowledged_by": sorted({str(v.get("acknowledged_by") or v.get("recorded_by") or "") for v in acks if str(v.get("acknowledged_by") or v.get("recorded_by") or "")}), "read_by": sorted(reads.get(note_id, set()))})
    return sorted(result, key=lambda item: (str(item.get("recorded_at") or ""), str(item.get("collaboration_note_id") or "")))


def find_note(case_id: str, note_id: str) -> dict[str, Any] | None:
    return next((item for item in current_notes(case_id) if item.get("collaboration_note_id") == note_id), None)


def build_collaboration_notes_workspace(case_id: str, *, user_identity: str | None = None) -> dict[str, Any]:
    all_history = history(case_id)
    notes = current_notes(case_id)
    user = str(user_identity or "").strip()
    active = [item for item in notes if item.get("note_status") == "active"]
    unread = [item for item in active if user and user in set(item.get("mentioned_users") or []) and user not in set(item.get("read_by") or [])]
    required = [item for item in active if item.get("acknowledgement_required") and user and user != item.get("author") and user not in set(item.get("acknowledged_by") or [])]
    return {
        "schema": "socmint.collaboration_notes_mentions.v26_2",
        "version": "v26.2.0",
        "status": "attention_required" if unread or required else "ready",
        "case_id": case_id,
        "user_identity": user or None,
        "target_types": list(TARGET_TYPES),
        "visibility_scopes": list(VISIBILITY_SCOPES),
        "priorities": list(PRIORITIES),
        "notes": notes,
        "active_notes": active,
        "active_note_count": len(active),
        "unread_mentions": unread,
        "unread_mention_count": len(unread),
        "acknowledgement_required": required,
        "acknowledgement_required_count": len(required),
        "history": all_history,
        "history_count": len(all_history),
        "read_only_view_created_record": False,
        "source_records_mutated": False,
        "case_access_scope_changed": False,
        "access_granted_by_mention": False,
        "next_action": "manage_collaboration_notes",
    }
