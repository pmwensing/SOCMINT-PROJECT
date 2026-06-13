from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from . import database


PERSISTENT_CASE_REVIEW_DECISIONS_SCHEMA = (
    "socmint.persistent_case_review_decisions.v19_0"
)
VERSION = "v19.0.0"
AUDIT_ACTION = "case_intelligence_review_decision"


def _ensure_audit_storage() -> None:
    database.ensure_configured()
    database.AuditLog.__table__.create(bind=database.engine, checkfirst=True)


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


def list_persistent_case_review_decisions(
    case_id: str,
    *,
    limit: int = 100,
) -> dict[str, Any]:
    _ensure_audit_storage()
    session = database.Session()
    try:
        rows = (
            session.query(database.AuditLog)
            .filter_by(action=AUDIT_ACTION, target_value=case_id)
            .order_by(database.AuditLog.created_at.desc(), database.AuditLog.id.desc())
            .limit(max(1, min(int(limit), 500)))
            .all()
        )
        entries = []
        for row in rows:
            try:
                details = json.loads(row.details or "{}")
            except json.JSONDecodeError:
                details = {}
            entries.append(
                {
                    "decision_record_id": row.id,
                    "case_id": row.target_value,
                    "actor": row.actor,
                    "decision": details.get("decision"),
                    "note": details.get("note"),
                    "source_recorded_at": details.get("recorded_at"),
                    "persisted_at": row.created_at.isoformat()
                    if row.created_at
                    else None,
                    "ip_address": row.ip_address,
                }
            )
        return {
            "schema": PERSISTENT_CASE_REVIEW_DECISIONS_SCHEMA,
            "version": VERSION,
            "status": "available",
            "case_id": case_id,
            "entry_count": len(entries),
            "entries": entries,
            "persistence": "audit_logs",
            "next_action": "review_case_intelligence_workspace",
        }
    finally:
        session.close()
