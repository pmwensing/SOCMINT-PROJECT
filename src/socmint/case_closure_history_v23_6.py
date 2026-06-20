from __future__ import annotations

from typing import Any

from . import database
from .dossier_assembly_workspace_v21_0 import _ensure_storage, _json_details

SCHEMA = "socmint.case_closure_archive_history.v23_6"
VERSION = "v23.6.0"

ACTIONS = {
    "case_closure_readiness_review": "readiness_review",
    "case_supervisor_closure_decision": "closure_decision",
    "case_retention_policy_assignment": "retention_assignment",
    "case_archive_package_generated": "archive_generation",
    "case_reopen_request": "reopen_request",
    "case_reopen_authorization": "reopen_authorization",
}


def _events(case_id: str) -> list[dict[str, Any]]:
    _ensure_storage()
    session = database.Session()
    try:
        rows = (
            session.query(database.AuditLog)
            .filter(database.AuditLog.target_value == case_id)
            .filter(database.AuditLog.action.in_(ACTIONS))
            .order_by(database.AuditLog.created_at.asc(), database.AuditLog.id.asc())
            .all()
        )
        return [
            {
                "timeline_id": row.id,
                "event_type": ACTIONS[row.action],
                "action": row.action,
                "actor": row.actor,
                "occurred_at": row.created_at.isoformat() if row.created_at else None,
                "details": _json_details(row),
            }
            for row in rows
        ]
    finally:
        session.close()


def build_case_closure_history(case_id: str) -> dict[str, Any]:
    timeline = _events(case_id)
    latest: dict[str, dict[str, Any]] = {}
    for event in timeline:
        latest[event["event_type"]] = event

    readiness = (latest.get("readiness_review") or {}).get("details") or {}
    closure = (latest.get("closure_decision") or {}).get("details") or {}
    retention = (latest.get("retention_assignment") or {}).get("details") or {}
    archive = (latest.get("archive_generation") or {}).get("details") or {}
    reopen_request = (latest.get("reopen_request") or {}).get("details") or {}
    reopen_authorization = (latest.get("reopen_authorization") or {}).get(
        "details"
    ) or {}

    authorization_decision = reopen_authorization.get("decision")
    case_reopened = reopen_authorization.get("case_reopen_authorized") is True
    if case_reopened:
        closure_state = "reopened"
    elif closure.get("decision") == "close":
        closure_state = "closed"
    elif closure.get("decision") in {"hold", "return"}:
        closure_state = closure.get("decision")
    elif readiness.get("decision") == "ready":
        closure_state = "ready_for_closure_decision"
    else:
        closure_state = "open"

    archive_state = (
        "generated" if archive.get("archive_package_id") else "not_generated"
    )
    reopen_status = (
        "authorized"
        if authorization_decision == "authorize"
        else "denied"
        if authorization_decision == "deny"
        else "pending_authorization"
        if reopen_request.get("reopen_request_id")
        else "none"
    )

    unresolved: list[dict[str, str]] = []
    if readiness.get("decision") != "ready" and not closure:
        unresolved.append({"key": "closure_readiness_review_required"})
    if readiness.get("decision") == "ready" and not closure:
        unresolved.append({"key": "supervisor_closure_decision_required"})
    if closure.get("decision") == "close" and not retention:
        unresolved.append({"key": "retention_assignment_required"})
    if retention and not archive:
        unresolved.append({"key": "archive_package_generation_required"})
    if reopen_request and not reopen_authorization:
        unresolved.append({"key": "reopen_authorization_required"})
    if closure.get("decision") == "hold":
        unresolved.append({"key": "closure_hold_resolution_required"})
    if closure.get("decision") == "return":
        unresolved.append({"key": "closure_return_resolution_required"})

    retention_disposition = retention.get("disposition") or None
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "case_id": case_id,
        "status": "complete" if not unresolved else "attention_required",
        "timeline": timeline,
        "event_count": len(timeline),
        "current_closure_state": closure_state,
        "current_archive_state": archive_state,
        "retention_disposition": retention_disposition,
        "reopen_status": reopen_status,
        "unresolved_actions": unresolved,
        "unresolved_action_count": len(unresolved),
        "latest_events": latest,
        "source_records_mutated": False,
        "history_record_created": False,
        "next_action": unresolved[0]["key"]
        if unresolved
        else "product_review_checkpoint",
    }
