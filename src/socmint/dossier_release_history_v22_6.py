from __future__ import annotations

from typing import Any

from . import database
from .dossier_assembly_workspace_v21_0 import _ensure_storage, _json_details

SCHEMA = "socmint.dossier_release_history.v22_6"
VERSION = "v22.6.0"

ACTION_MAP = {
    "case_dossier_release_authorization": "authorization",
    "case_dossier_release_preview": "preview",
    "case_dossier_secure_distribution": "dispatch",
    "case_dossier_delivery_receipt": "delivery_receipt",
    "case_dossier_recipient_acknowledgement": "recipient_acknowledgement",
    "case_dossier_failed_delivery_review": "failed_delivery_review",
    "case_dossier_recall_request": "recall",
    "case_dossier_reissue_authorization": "reissue",
}


def _timeline(case_id: str) -> list[dict[str, Any]]:
    _ensure_storage()
    session = database.Session()
    try:
        rows = (
            session.query(database.AuditLog)
            .filter(database.AuditLog.target_value == case_id)
            .filter(database.AuditLog.action.in_(tuple(ACTION_MAP)))
            .order_by(database.AuditLog.created_at.asc(), database.AuditLog.id.asc())
            .all()
        )
        return [
            {
                "event_id": row.id,
                "event_type": ACTION_MAP[row.action],
                "action": row.action,
                "actor": row.actor,
                "recorded_at": row.created_at.isoformat() if row.created_at else None,
                "details": _json_details(row),
            }
            for row in rows
        ]
    finally:
        session.close()


def build_release_delivery_history(case_id: str) -> dict[str, Any]:
    timeline = _timeline(case_id)
    latest: dict[str, dict[str, Any]] = {}
    for event in timeline:
        latest[event["event_type"]] = event

    receipt = (latest.get("delivery_receipt") or {}).get("details") or {}
    acknowledgement = (latest.get("recipient_acknowledgement") or {}).get("details") or {}
    recall = (latest.get("recall") or {}).get("details") or {}
    reissue = (latest.get("reissue") or {}).get("details") or {}
    dispatch = (latest.get("dispatch") or {}).get("details") or {}

    unresolved: list[dict[str, str]] = []
    delivery_result = receipt.get("delivery_result")
    if dispatch and not receipt:
        unresolved.append({"key": "delivery_receipt_outstanding"})
    if delivery_result == "delivered" and not acknowledgement:
        unresolved.append({"key": "recipient_acknowledgement_outstanding"})
    if delivery_result == "failed" and "failed_delivery_review" not in latest:
        unresolved.append({"key": "failed_delivery_review_outstanding"})
    if recall and not reissue and delivery_result != "delivered":
        unresolved.append({"key": "recall_outcome_or_reissue_outstanding"})

    if acknowledgement:
        outcome = "delivered_and_acknowledged"
    elif delivery_result == "delivered":
        outcome = "delivered_acknowledgement_pending"
    elif reissue:
        outcome = "reissue_authorized"
    elif recall:
        outcome = "recall_requested"
    elif delivery_result == "failed":
        outcome = "delivery_failed"
    elif dispatch:
        outcome = "dispatched_receipt_pending"
    elif "authorization" in latest:
        outcome = "authorized_not_dispatched"
    else:
        outcome = "not_started"

    closure_ready = bool(acknowledgement) and not unresolved
    summary = {
        "case_id": case_id,
        "release_outcome": outcome,
        "closure_ready": closure_ready,
        "event_count": len(timeline),
        "authorization_id": ((latest.get("authorization") or {}).get("details") or {}).get("authorization_id"),
        "distribution_id": dispatch.get("distribution_id"),
        "delivery_receipt_id": receipt.get("delivery_receipt_id"),
        "acknowledgement_id": acknowledgement.get("acknowledgement_id"),
        "recall_request_id": recall.get("recall_request_id"),
        "reissue_authorization_id": reissue.get("reissue_authorization_id"),
        "unresolved_action_count": len(unresolved),
        "unresolved_actions": unresolved,
    }
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "case_id": case_id,
        "status": "closure_ready" if closure_ready else "open",
        "current_release_outcome": outcome,
        "timeline": timeline,
        "timeline_event_count": len(timeline),
        "unresolved_actions": unresolved,
        "unresolved_action_count": len(unresolved),
        "closure_ready": closure_ready,
        "closure_summary": summary,
        "source_records_mutated": False,
        "next_action": "close_release_case" if closure_ready else (unresolved[0]["key"] if unresolved else "continue_release_workflow"),
    }
