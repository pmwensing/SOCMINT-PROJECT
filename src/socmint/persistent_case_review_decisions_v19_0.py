from __future__ import annotations

import json
from copy import deepcopy
from datetime import date, datetime
from math import ceil
from typing import Any

from . import database


PERSISTENT_CASE_REVIEW_DECISIONS_SCHEMA = (
    "socmint.persistent_case_review_decisions.v19_0"
)
VERSION = "v19.2.0"
AUDIT_ACTION = "case_intelligence_review_decision"
REVIEW_ACTION = "case_intelligence_review_decision_state"
REVIEW_STATES = {"unreviewed", "reviewed", "needs_follow_up", "accepted"}


def _ensure_audit_storage() -> None:
    database.ensure_configured()
    database.AuditLog.__table__.create(bind=database.engine, checkfirst=True)


def _json_details(row) -> dict[str, Any]:
    try:
        value = json.loads(row.details or "{}")
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(str(value))
        except ValueError:
            return None


def persist_case_review_decision(
    case_id: str,
    decision: dict[str, Any],
    *,
    actor: str,
    ip_address: str | None = None,
) -> dict[str, Any]:
    safe = deepcopy(decision or {})
    if safe.get("status") != "recorded":
        return {
            "schema": PERSISTENT_CASE_REVIEW_DECISIONS_SCHEMA,
            "version": VERSION,
            "status": "blocked",
            "persisted": False,
            "case_id": case_id,
            "blockers": [
                {
                    "key": "decision_not_recorded",
                    "detail": "only a validated recorded decision can be persisted",
                }
            ],
            "next_action": "record_valid_case_review_decision",
        }

    _ensure_audit_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=actor,
            action=AUDIT_ACTION,
            target_value=case_id,
            ip_address=ip_address,
            details=json.dumps(
                {
                    "case_id": case_id,
                    "decision": safe.get("decision"),
                    "note": safe.get("note"),
                    "recorded_at": safe.get("recorded_at"),
                    "source_status": safe.get("status"),
                    "source_version": "v18.5",
                },
                sort_keys=True,
            ),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return {
            "schema": PERSISTENT_CASE_REVIEW_DECISIONS_SCHEMA,
            "version": VERSION,
            "status": "persisted",
            "persisted": True,
            "case_id": case_id,
            "decision_record_id": row.id,
            "actor": row.actor,
            "decision": safe.get("decision"),
            "recorded_at": row.created_at.isoformat() if row.created_at else None,
            "next_action": "review_persistent_case_decisions",
        }
    finally:
        session.close()


def set_persistent_decision_review_state(
    case_id: str,
    decision_record_id: int,
    review_state: str,
    *,
    actor: str,
    note: str = "",
    ip_address: str | None = None,
) -> dict[str, Any]:
    state = str(review_state or "").strip()
    if state not in REVIEW_STATES:
        return {
            "status": "blocked",
            "blockers": [{"key": "unsupported_review_state", "detail": state or "missing"}],
            "next_action": "choose_supported_review_state",
        }

    _ensure_audit_storage()
    session = database.Session()
    try:
        source = (
            session.query(database.AuditLog)
            .filter_by(id=int(decision_record_id), action=AUDIT_ACTION, target_value=case_id)
            .one_or_none()
        )
        if source is None:
            return {
                "status": "blocked",
                "blockers": [{"key": "decision_record_not_found", "detail": str(decision_record_id)}],
                "next_action": "refresh_persistent_decision_history",
            }
        annotation = database.AuditLog(
            actor=actor,
            action=REVIEW_ACTION,
            target_value=case_id,
            ip_address=ip_address,
            details=json.dumps(
                {
                    "case_id": case_id,
                    "decision_record_id": source.id,
                    "review_state": state,
                    "review_note": str(note or "").strip(),
                },
                sort_keys=True,
            ),
        )
        session.add(annotation)
        session.commit()
        session.refresh(annotation)
        return {
            "status": "recorded",
            "case_id": case_id,
            "decision_record_id": source.id,
            "review_state": state,
            "reviewed_by": actor,
            "review_note": str(note or "").strip(),
            "reviewed_at": annotation.created_at.isoformat() if annotation.created_at else None,
            "annotation_record_id": annotation.id,
            "original_decision_mutated": False,
            "next_action": "refresh_persistent_decision_history",
        }
    finally:
        session.close()


def list_persistent_case_review_decisions(
    case_id: str,
    *,
    actor: str | None = None,
    decision: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    review_state: str | None = None,
    page: int = 1,
    page_size: int = 25,
    limit: int | None = None,
) -> dict[str, Any]:
    _ensure_audit_storage()
    session = database.Session()
    try:
        rows = (
            session.query(database.AuditLog)
            .filter_by(action=AUDIT_ACTION, target_value=case_id)
            .order_by(database.AuditLog.created_at.desc(), database.AuditLog.id.desc())
            .all()
        )
        annotations = (
            session.query(database.AuditLog)
            .filter_by(action=REVIEW_ACTION, target_value=case_id)
            .order_by(database.AuditLog.created_at.asc(), database.AuditLog.id.asc())
            .all()
        )
        latest_annotations: dict[int, dict[str, Any]] = {}
        for row in annotations:
            details = _json_details(row)
            record_id = details.get("decision_record_id")
            if isinstance(record_id, int):
                latest_annotations[record_id] = {
                    "review_state": details.get("review_state") or "unreviewed",
                    "review_note": details.get("review_note") or "",
                    "reviewed_by": row.actor,
                    "reviewed_at": row.created_at.isoformat() if row.created_at else None,
                    "annotation_record_id": row.id,
                }

        entries = []
        start_date = _parse_date(date_from)
        end_date = _parse_date(date_to)
        for row in rows:
            details = _json_details(row)
            persisted_date = row.created_at.date() if row.created_at else None
            annotation = latest_annotations.get(
                row.id,
                {
                    "review_state": "unreviewed",
                    "review_note": "",
                    "reviewed_by": None,
                    "reviewed_at": None,
                    "annotation_record_id": None,
                },
            )
            entry = {
                "decision_record_id": row.id,
                "case_id": row.target_value,
                "actor": row.actor,
                "decision": details.get("decision"),
                "note": details.get("note"),
                "source_recorded_at": details.get("recorded_at"),
                "persisted_at": row.created_at.isoformat() if row.created_at else None,
                "ip_address": row.ip_address,
                **annotation,
            }
            if actor and entry["actor"] != actor:
                continue
            if decision and entry["decision"] != decision:
                continue
            if start_date and (persisted_date is None or persisted_date < start_date):
                continue
            if end_date and (persisted_date is None or persisted_date > end_date):
                continue
            if review_state and entry["review_state"] != review_state:
                continue
            entries.append(entry)

        if limit is not None:
            page_size = int(limit)
        safe_page = max(1, int(page))
        safe_page_size = max(1, min(int(page_size), 100))
        total_entries = len(entries)
        page_count = max(1, ceil(total_entries / safe_page_size)) if total_entries else 0
        offset = (safe_page - 1) * safe_page_size
        page_entries = entries[offset : offset + safe_page_size]
        return {
            "schema": PERSISTENT_CASE_REVIEW_DECISIONS_SCHEMA,
            "version": VERSION,
            "status": "available",
            "case_id": case_id,
            "entry_count": len(page_entries),
            "total_entries": total_entries,
            "entries": page_entries,
            "filters": {
                "actor": actor,
                "decision": decision,
                "date_from": date_from,
                "date_to": date_to,
                "review_state": review_state,
            },
            "pagination": {
                "page": safe_page,
                "page_size": safe_page_size,
                "page_count": page_count,
                "has_previous": safe_page > 1,
                "has_next": safe_page < page_count,
            },
            "review_states": sorted(REVIEW_STATES),
            "persistence": "audit_logs",
            "original_records_mutated": False,
            "next_action": "review_case_intelligence_workspace",
        }
    finally:
        session.close()
