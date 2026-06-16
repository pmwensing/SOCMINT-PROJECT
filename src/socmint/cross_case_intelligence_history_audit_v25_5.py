from __future__ import annotations

import datetime as dt
from collections import Counter
from typing import Any

from . import database
from .cross_case_confirmed_link_registry_v25_2 import (
    ACTION as CONFIRMED_LINK_ACTION,
    build_confirmed_link_registry_workspace,
)
from .cross_case_correlation_review_v25_1 import ACTION as REVIEW_ACTION
from .cross_case_intelligence_workspace_v25_0 import (
    build_cross_case_intelligence_workspace,
)
from .cross_case_link_impact_analysis_v25_4 import (
    build_cross_case_link_impact_analysis,
)
from .cross_case_relationship_graph_v25_3 import (
    build_cross_case_relationship_graph,
)
from .dossier_assembly_workspace_v21_0 import _ensure_storage, _json_details, _sha

SCHEMA = "socmint.cross_case_intelligence_history_audit.v25_5"
VERSION = "v25.5.0"


def _review_visible(details: dict[str, Any], allowed_case_ids: set[str] | None) -> bool:
    if allowed_case_ids is None:
        return True
    candidate = details.get("candidate_snapshot") or {}
    case_ids = {str(value) for value in candidate.get("case_ids") or []}
    return bool(case_ids) and all(case_id in allowed_case_ids for case_id in case_ids)


def _link_visible(details: dict[str, Any], allowed_case_ids: set[str] | None) -> bool:
    if allowed_case_ids is None:
        return True
    case_ids = {str(value) for value in details.get("case_ids") or []}
    return bool(case_ids) and all(case_id in allowed_case_ids for case_id in case_ids)


def _persisted_events(allowed_case_ids: set[str] | None) -> list[dict[str, Any]]:
    _ensure_storage()
    session = database.Session()
    try:
        rows = (
            session.query(database.AuditLog)
            .filter(database.AuditLog.action.in_((REVIEW_ACTION, CONFIRMED_LINK_ACTION)))
            .order_by(database.AuditLog.created_at.asc(), database.AuditLog.id.asc())
            .all()
        )
        events: list[dict[str, Any]] = []
        for row in rows:
            details = _json_details(row)
            if row.action == REVIEW_ACTION:
                if not _review_visible(details, allowed_case_ids):
                    continue
                event_type = "analyst_decision"
                correlation_id = details.get("correlation_id") or row.target_value
                case_ids = (details.get("candidate_snapshot") or {}).get("case_ids") or []
            else:
                if not _link_visible(details, allowed_case_ids):
                    continue
                event_type = "confirmed_link_registration"
                correlation_id = details.get("correlation_id") or row.target_value
                case_ids = details.get("case_ids") or []

            binding = {
                "record_id": row.id,
                "action": row.action,
                "target_value": row.target_value,
                "details": details,
            }
            events.append({
                "history_event_id": f"audit-{row.id}",
                "event_type": event_type,
                "occurred_at": row.created_at.isoformat() if row.created_at else None,
                "actor": row.actor,
                "correlation_id": correlation_id,
                "confirmed_link_id": details.get("confirmed_link_id"),
                "case_ids": sorted(str(value) for value in case_ids),
                "source_action": row.action,
                "source_record_id": row.id,
                "source_binding": binding,
                "source_binding_sha256": _sha(binding),
                "access_scope": (
                    details.get("workspace_access_scope")
                    if row.action == REVIEW_ACTION
                    else (details.get("accepted_review") or {}).get("workspace_access_scope")
                ),
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
    correlation_id: str | None = None,
    confirmed_link_id: str | None = None,
    case_ids: list[str] | None = None,
    access_scope: dict[str, Any] | None = None,
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
        "correlation_id": correlation_id,
        "confirmed_link_id": confirmed_link_id,
        "case_ids": sorted(case_ids or []),
        "source_action": None,
        "source_record_id": None,
        "source_binding": binding,
        "source_binding_sha256": digest,
        "access_scope": access_scope,
        "details": source,
        "synthetic_checkpoint": True,
    }


def build_cross_case_intelligence_history_audit(
    *,
    allowed_case_ids: set[str] | None = None,
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    current_time = now or dt.datetime.now(dt.UTC)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=dt.UTC)
    occurred_at = current_time.isoformat()

    candidate_workspace = build_cross_case_intelligence_workspace(
        allowed_case_ids=allowed_case_ids
    )
    registry_workspace = build_confirmed_link_registry_workspace(
        allowed_case_ids=allowed_case_ids
    )
    graph = build_cross_case_relationship_graph(
        allowed_case_ids=allowed_case_ids
    )

    events = _persisted_events(allowed_case_ids)
    events.append(
        _checkpoint(
            "candidate_discovery",
            occurred_at,
            candidate_workspace,
            access_scope=candidate_workspace.get("access_scope"),
            case_ids=list(candidate_workspace.get("access_scope", {}).get("visible_case_ids") or []),
        )
    )
    events.append(
        _checkpoint(
            "graph_projection",
            occurred_at,
            graph,
            access_scope=graph.get("access_scope"),
            case_ids=list(graph.get("access_scope", {}).get("allowed_case_ids") or []),
        )
    )

    impact_analyses: list[dict[str, Any]] = []
    for link in registry_workspace.get("confirmed_links") or []:
        link_id = str(link.get("confirmed_link_id") or "").strip()
        if not link_id:
            continue
        impact = build_cross_case_link_impact_analysis(
            link_id,
            allowed_case_ids=allowed_case_ids,
        )
        if impact.get("status") != "ready":
            continue
        impact_analyses.append(impact)
        events.append(
            _checkpoint(
                "impact_analysis",
                occurred_at,
                impact,
                confirmed_link_id=link_id,
                case_ids=list(impact.get("impact", {}).get("affected_case_ids") or []),
                access_scope=impact.get("access_scope"),
            )
        )

    events.sort(
        key=lambda item: (
            item.get("occurred_at") or "",
            int(item.get("source_record_id") or 10**18),
            item["history_event_id"],
        )
    )

    event_counts = Counter(item["event_type"] for item in events)
    actor_counts = Counter(str(item.get("actor") or "unknown") for item in events)
    current_state = {
        "candidate_discovery": {
            "status": candidate_workspace.get("status"),
            "counts": candidate_workspace.get("counts"),
            "minimum_case_count": candidate_workspace.get("minimum_case_count"),
            "access_scope": candidate_workspace.get("access_scope"),
        },
        "reviews": {
            "disposition_counts": registry_workspace.get("review_disposition_counts"),
            "accepted_pending_count": registry_workspace.get("accepted_pending_count"),
            "reviewed_correlation_count": len(registry_workspace.get("review_histories") or {}),
        },
        "confirmed_links": {
            "count": registry_workspace.get("confirmed_link_count"),
            "confirmed_link_ids": sorted(
                str(item.get("confirmed_link_id"))
                for item in registry_workspace.get("confirmed_links") or []
                if item.get("confirmed_link_id")
            ),
        },
        "relationship_graph": {
            "status": graph.get("status"),
            "graph_sha256": graph.get("graph_sha256"),
            "counts": graph.get("counts"),
        },
        "impact_analyses": {
            "count": len(impact_analyses),
            "confirmed_link_ids": sorted(
                str(item.get("impact", {}).get("confirmed_link_id"))
                for item in impact_analyses
                if item.get("impact", {}).get("confirmed_link_id")
            ),
            "impact_sha256_values": sorted(
                str(item.get("impact_sha256"))
                for item in impact_analyses
                if item.get("impact_sha256")
            ),
        },
    }

    access_scope = {
        "mode": "restricted" if allowed_case_ids is not None else "all_visible_cases",
        "allowed_case_ids": sorted(allowed_case_ids) if allowed_case_ids is not None else None,
    }
    current_state["access_scope"] = access_scope

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "ready",
        "generated_at": occurred_at,
        "access_scope": access_scope,
        "history": events,
        "event_count": len(events),
        "event_type_counts": dict(sorted(event_counts.items())),
        "actor_counts": dict(sorted(actor_counts.items())),
        "correlation_count": len(
            {item.get("correlation_id") for item in events if item.get("correlation_id")}
        ),
        "confirmed_link_count": len(
            {item.get("confirmed_link_id") for item in events if item.get("confirmed_link_id")}
        ),
        "case_count": len(
            {
                case_id
                for item in events
                for case_id in item.get("case_ids") or []
            }
        ),
        "source_bound_event_count": sum(
            1 for item in events if item.get("source_binding_sha256")
        ),
        "current_cross_case_intelligence_state": current_state,
        "current_cross_case_intelligence_state_sha256": _sha(current_state),
        "source_records_mutated": False,
        "review_history_mutated": False,
        "confirmed_link_registry_mutated": False,
        "graph_mutated": False,
        "impact_records_created": False,
        "history_record_created": False,
        "next_action": "review_cross_case_intelligence_history",
    }
