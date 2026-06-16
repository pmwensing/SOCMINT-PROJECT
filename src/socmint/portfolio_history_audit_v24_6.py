from __future__ import annotations

import datetime as dt
from collections import Counter
from typing import Any

from . import database
from .dossier_assembly_workspace_v21_0 import _ensure_storage, _json_details, _sha
from .persistent_decision_supervisor_queue_v19_3 import ASSIGNMENT_ACTION
from .portfolio_blocked_overdue_queue_v24_3 import build_blocked_overdue_case_queue
from .portfolio_case_stage_overview_v24_1 import build_case_status_stage_overview
from .portfolio_operational_metrics_v24_5 import build_operational_metrics
from .portfolio_operations_dashboard_v24_0 import build_portfolio_operations_dashboard
from .portfolio_supervisor_escalation_v24_4 import ACTIONS as ESCALATION_ACTIONS
from .portfolio_workload_monitoring_v24_2 import build_workload_assignment_monitoring

SCHEMA = "socmint.portfolio_history_audit.v24_6"
VERSION = "v24.6.0"

STAGE_ACTIONS = {
    "case_closure_readiness_review",
    "case_supervisor_closure_decision",
    "case_retention_policy_assignment",
    "case_archive_package_generated",
    "case_reopen_request",
    "case_reopen_authorization",
    "dossier_final_export_package",
    "dossier_delivery_receipt",
    "dossier_recipient_acknowledgement",
}


def _audit_events() -> list[dict[str, Any]]:
    actions = STAGE_ACTIONS | {ASSIGNMENT_ACTION} | set(ESCALATION_ACTIONS.values())
    _ensure_storage()
    session = database.Session()
    try:
        rows = (
            session.query(database.AuditLog)
            .filter(database.AuditLog.action.in_(tuple(actions)))
            .order_by(database.AuditLog.created_at.asc(), database.AuditLog.id.asc())
            .all()
        )
        events = []
        for row in rows:
            details = _json_details(row)
            if row.action in STAGE_ACTIONS:
                event_type = "stage_transition"
            elif row.action == ASSIGNMENT_ACTION:
                event_type = "assignment"
            else:
                event_type = "escalation_control"
            binding = {
                "record_id": row.id,
                "action": row.action,
                "case_id": row.target_value,
                "details": details,
            }
            events.append({
                "history_event_id": f"audit-{row.id}",
                "event_type": event_type,
                "occurred_at": row.created_at.isoformat() if row.created_at else None,
                "actor": row.actor,
                "case_id": row.target_value,
                "source_action": row.action,
                "source_record_id": row.id,
                "source_binding": binding,
                "source_binding_sha256": _sha(binding),
                "details": details,
                "synthetic_checkpoint": False,
            })
        return events
    finally:
        session.close()


def _checkpoint(
    event_type: str,
    occurred_at: str,
    source: dict[str, Any],
    *,
    actor: str = "system",
) -> dict[str, Any]:
    binding = {
        "schema": source.get("schema"),
        "version": source.get("version"),
        "status": source.get("status"),
        "source": source,
    }
    digest = _sha(binding)
    return {
        "history_event_id": f"{event_type}-{digest[:24]}",
        "event_type": event_type,
        "occurred_at": occurred_at,
        "actor": actor,
        "case_id": None,
        "source_action": None,
        "source_record_id": None,
        "source_binding": binding,
        "source_binding_sha256": digest,
        "details": source,
        "synthetic_checkpoint": True,
    }


def build_portfolio_history_audit(
    *, now: dt.datetime | None = None
) -> dict[str, Any]:
    current_time = now or dt.datetime.now(dt.UTC)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=dt.UTC)

    portfolio = build_portfolio_operations_dashboard()
    stage = build_case_status_stage_overview(now=current_time)
    workload = build_workload_assignment_monitoring(now=current_time)
    blocked = build_blocked_overdue_case_queue()
    metrics = build_operational_metrics(now=current_time)

    occurred_at = current_time.isoformat()
    events = _audit_events()
    events.extend([
        _checkpoint("portfolio_snapshot", occurred_at, portfolio),
        _checkpoint("stage_snapshot", occurred_at, stage),
        _checkpoint("assignment_snapshot", occurred_at, workload),
        _checkpoint("blocked_overdue_detection", occurred_at, blocked),
        _checkpoint("metrics_checkpoint", occurred_at, metrics),
    ])
    events.sort(key=lambda item: (
        item.get("occurred_at") or "",
        int(item.get("source_record_id") or 10**18),
        item["history_event_id"],
    ))

    counts = Counter(item["event_type"] for item in events)
    actors = Counter(str(item.get("actor") or "unknown") for item in events)
    current_state = {
        "portfolio": {
            "status": portfolio.get("status"),
            "counts": portfolio.get("counts"),
            "stage_counts": portfolio.get("stage_counts"),
        },
        "stages": {
            "case_count": stage.get("case_count"),
            "blocked_count": stage.get("blocked_count"),
            "stage_counts": stage.get("stage_counts"),
        },
        "assignments": {
            "status": workload.get("status"),
            "counts": workload.get("counts"),
            "workload_balance": workload.get("workload_balance"),
        },
        "blocked_overdue": {
            "status": blocked.get("status"),
            "counts": blocked.get("counts"),
            "thresholds": blocked.get("thresholds"),
        },
        "metrics": {
            "case_volume": metrics.get("case_volume"),
            "completion_counts": metrics.get("completion_counts"),
            "rates": metrics.get("rates"),
        },
    }
    current_state_sha256 = _sha(current_state)

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "ready",
        "generated_at": occurred_at,
        "history": events,
        "event_count": len(events),
        "event_type_counts": dict(sorted(counts.items())),
        "actor_counts": dict(sorted(actors.items())),
        "case_count": len({item.get("case_id") for item in events if item.get("case_id")}),
        "source_bound_event_count": sum(1 for item in events if item.get("source_binding_sha256")),
        "current_portfolio_state": current_state,
        "current_portfolio_state_sha256": current_state_sha256,
        "source_records_mutated": False,
        "history_record_created": False,
        "next_action": "review_portfolio_history",
    }
