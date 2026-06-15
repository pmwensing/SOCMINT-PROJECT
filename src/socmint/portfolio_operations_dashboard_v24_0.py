from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from typing import Any

from . import database
from .dossier_assembly_workspace_v21_0 import _ensure_storage, _json_details

SCHEMA = "socmint.portfolio_operations_dashboard.v24_0"
VERSION = "v24.0.0"

CASE_ACTION_PREFIXES = (
    "case_",
    "persistent_case_",
    "dossier_",
)


def _configured_case_ids() -> list[str]:
    raw = os.getenv("SOCMINT_PORTFOLIO_CASES", "").strip()
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        value = [item.strip() for item in raw.split(",") if item.strip()]
    if isinstance(value, list):
        return sorted({str(item).strip() for item in value if str(item).strip()})
    return []


def _case_events() -> dict[str, list[dict[str, Any]]]:
    _ensure_storage()
    session = database.Session()
    try:
        rows = (
            session.query(database.AuditLog)
            .filter(database.AuditLog.target_value.isnot(None))
            .order_by(database.AuditLog.created_at.asc(), database.AuditLog.id.asc())
            .all()
        )
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            action = str(row.action or "")
            if not action.startswith(CASE_ACTION_PREFIXES):
                continue
            case_id = str(row.target_value or "").strip()
            if not case_id:
                continue
            grouped[case_id].append({
                "record_id": row.id,
                "action": action,
                "actor": row.actor,
                "occurred_at": row.created_at.isoformat() if row.created_at else None,
                "details": _json_details(row),
            })
        return dict(grouped)
    finally:
        session.close()


def _derive_case(case_id: str, events: list[dict[str, Any]]) -> dict[str, Any]:
    latest_by_action: dict[str, dict[str, Any]] = {}
    blocked_events = []
    for event in events:
        latest_by_action[event["action"]] = event
        details = event.get("details") or {}
        if details.get("status") in {"blocked", "attention_required", "failed"}:
            blocked_events.append(event)
        if details.get("blockers"):
            blocked_events.append(event)

    reopen = latest_by_action.get("case_reopen_authorization")
    archive = latest_by_action.get("case_archive_package_generated")
    closure = latest_by_action.get("case_supervisor_closure_decision")
    acknowledgement = latest_by_action.get("dossier_recipient_acknowledgement")
    receipt = latest_by_action.get("dossier_delivery_receipt")
    export = latest_by_action.get("dossier_final_export_package")
    retention = latest_by_action.get("case_retention_policy_assignment")
    readiness = latest_by_action.get("case_closure_readiness_review")

    if reopen and (reopen.get("details") or {}).get("decision") == "authorize":
        stage = "reopened"
    elif archive:
        stage = "archived"
    elif closure and (closure.get("details") or {}).get("decision") == "close":
        stage = "closed"
    elif acknowledgement or receipt:
        stage = "delivered"
    elif export:
        stage = "dossier_exported"
    elif retention:
        stage = "retention_pending_archive"
    elif readiness:
        stage = "closure_review"
    elif events:
        stage = "active"
    else:
        stage = "unstarted"

    latest = events[-1] if events else None
    blockers = []
    for event in blocked_events[-5:]:
        details = event.get("details") or {}
        for blocker in details.get("blockers") or []:
            key = str(blocker.get("key") or "portfolio_attention_required")
            if key not in {item["key"] for item in blockers}:
                blockers.append({"key": key, "source_action": event["action"]})

    return {
        "case_id": case_id,
        "stage": stage,
        "status": "blocked" if blockers else "operational",
        "blocked": bool(blockers),
        "blockers": blockers,
        "event_count": len(events),
        "latest_action": latest.get("action") if latest else None,
        "latest_actor": latest.get("actor") if latest else None,
        "latest_activity_at": latest.get("occurred_at") if latest else None,
        "retention_disposition": (
            (retention.get("details") or {}).get("disposition") if retention else None
        ),
        "links": {
            "case_review": f"/case-intelligence-review/{case_id}",
            "dossier_assembly": f"/dossier-assembly/{case_id}",
            "release_workspace": f"/dossier-release/{case_id}",
            "closure_workspace": f"/case-closure/{case_id}",
            "closure_history": f"/case-closure/{case_id}/history",
            "delivery_workspace": f"/case-delivery?case_id={case_id}",
        },
    }


def build_portfolio_operations_dashboard() -> dict[str, Any]:
    grouped = _case_events()
    case_ids = sorted(set(grouped) | set(_configured_case_ids()))
    cases = [_derive_case(case_id, grouped.get(case_id, [])) for case_id in case_ids]
    stage_counts = Counter(item["stage"] for item in cases)

    counts = {
        "total": len(cases),
        "active": sum(1 for item in cases if item["stage"] in {
            "active", "closure_review", "dossier_exported", "retention_pending_archive"
        }),
        "blocked": sum(1 for item in cases if item["blocked"]),
        "delivered": stage_counts.get("delivered", 0),
        "closed": stage_counts.get("closed", 0),
        "archived": stage_counts.get("archived", 0),
        "reopened": stage_counts.get("reopened", 0),
        "unstarted": stage_counts.get("unstarted", 0),
    }

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "ready",
        "counts": counts,
        "stage_counts": dict(sorted(stage_counts.items())),
        "cases": sorted(
            cases,
            key=lambda item: (item.get("latest_activity_at") or "", item["case_id"]),
            reverse=True,
        ),
        "blocked_cases": [item for item in cases if item["blocked"]],
        "source_records_mutated": False,
        "portfolio_record_created": False,
        "next_action": "review_portfolio_operations",
    }
