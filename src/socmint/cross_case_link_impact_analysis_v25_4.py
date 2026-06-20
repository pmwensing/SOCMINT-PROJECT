from __future__ import annotations

from collections import Counter
from typing import Any

from . import database
from .case_closure_history_v23_6 import build_case_closure_history
from .cross_case_confirmed_link_registry_v25_2 import confirmed_link_registry
from .cross_case_relationship_graph_v25_3 import build_cross_case_relationship_graph
from .dossier_assembly_workspace_v21_0 import _ensure_storage, _json_details, _sha
from .portfolio_workload_monitoring_v24_2 import build_workload_assignment_monitoring

SCHEMA = "socmint.cross_case_link_impact_analysis.v25_4"
VERSION = "v25.4.0"

PACKAGE_ACTIONS = {
    "dossier_final_export_package",
    "case_archive_package_generated",
    "dossier_delivery_receipt",
    "dossier_recipient_acknowledgement",
}


def _package_records(case_ids: set[str]) -> list[dict[str, Any]]:
    if not case_ids:
        return []
    _ensure_storage()
    session = database.Session()
    try:
        rows = (
            session.query(database.AuditLog)
            .filter(database.AuditLog.target_value.in_(tuple(sorted(case_ids))))
            .filter(database.AuditLog.action.in_(tuple(PACKAGE_ACTIONS)))
            .order_by(database.AuditLog.created_at.asc(), database.AuditLog.id.asc())
            .all()
        )
        return [
            {
                "case_id": str(row.target_value),
                "record_id": row.id,
                "action": row.action,
                "actor": row.actor,
                "occurred_at": row.created_at.isoformat() if row.created_at else None,
                "details": _json_details(row),
            }
            for row in rows
        ]
    finally:
        session.close()


def build_cross_case_link_impact_analysis(
    confirmed_link_id: str,
    *,
    allowed_case_ids: set[str] | None = None,
    links: list[dict[str, Any]] | None = None,
    graph: dict[str, Any] | None = None,
    workload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    registry = (
        links
        if links is not None
        else confirmed_link_registry(allowed_case_ids=allowed_case_ids)
    )
    link = next(
        (
            item
            for item in registry
            if item.get("confirmed_link_id") == confirmed_link_id
        ),
        None,
    )
    if link is None:
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "confirmed_link_id": confirmed_link_id,
            "status": "blocked",
            "blockers": [{"key": "visible_confirmed_link_required"}],
            "confirmed_link_mutated": False,
            "graph_mutated": False,
        }

    case_ids = sorted(
        {str(value) for value in link.get("case_ids") or [] if str(value)}
    )
    case_set = set(case_ids)
    if allowed_case_ids is not None and any(
        case_id not in allowed_case_ids for case_id in case_ids
    ):
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "confirmed_link_id": confirmed_link_id,
            "status": "blocked",
            "blockers": [{"key": "confirmed_link_case_access_required"}],
            "confirmed_link_mutated": False,
            "graph_mutated": False,
        }

    graph_payload = (
        graph
        if graph is not None
        else build_cross_case_relationship_graph(allowed_case_ids=allowed_case_ids)
    )
    workload_payload = (
        workload if workload is not None else build_workload_assignment_monitoring()
    )

    impacted_nodes = [
        node
        for node in graph_payload.get("graph", {}).get("nodes", [])
        if confirmed_link_id in (node.get("confirmed_link_ids") or [])
    ]
    impacted_edges = [
        edge
        for edge in graph_payload.get("graph", {}).get("edges", [])
        if edge.get("confirmed_link_id") == confirmed_link_id
    ]
    impacted_entities = [
        node
        for node in impacted_nodes
        if node.get("node_type")
        in {"entity", "identifier", "infrastructure", "evidence", "temporal"}
    ]

    workload_entries = [
        entry
        for entry in workload_payload.get("entries") or []
        if str(entry.get("case_id") or "") in case_set
    ]
    review_queues = []
    for entry in workload_entries:
        reviewer = str(entry.get("assigned_reviewer") or "").strip()
        review_queues.append(
            {
                "case_id": entry.get("case_id"),
                "review_state": entry.get("review_state"),
                "assigned_reviewer": reviewer or None,
                "assignment_age_hours": entry.get("assignment_age_hours"),
                "reviewer_queue": "/case-intelligence-review/my-assignments",
                "supervisor_queue": (
                    f"/case-intelligence-review/supervisor-queue?assigned_reviewer={reviewer}"
                    if reviewer
                    else "/case-intelligence-review/supervisor-queue"
                ),
            }
        )

    closure_states = []
    archive_records = []
    for case_id in case_ids:
        history = build_case_closure_history(case_id)
        closure_states.append(
            {
                "case_id": case_id,
                "current_closure_state": history.get("current_closure_state"),
                "current_archive_state": history.get("current_archive_state"),
                "retention_disposition": history.get("retention_disposition"),
                "reopen_status": history.get("reopen_status"),
                "unresolved_actions": history.get("unresolved_actions") or [],
                "history_event_count": history.get("event_count"),
            }
        )
        archive_event = (history.get("latest_events") or {}).get(
            "archive_generation"
        ) or {}
        if archive_event:
            archive_records.append(
                {
                    "case_id": case_id,
                    "timeline_id": archive_event.get("timeline_id"),
                    "actor": archive_event.get("actor"),
                    "occurred_at": archive_event.get("occurred_at"),
                    "details": archive_event.get("details") or {},
                }
            )

    package_records = _package_records(case_set)
    evidence_packages = [
        record
        for record in package_records
        if record.get("action")
        in {
            "dossier_final_export_package",
            "dossier_delivery_receipt",
            "dossier_recipient_acknowledgement",
        }
    ]
    archive_record_ids = {item.get("timeline_id") for item in archive_records}
    archive_records.extend(
        [
            record
            for record in package_records
            if record.get("action") == "case_archive_package_generated"
            and record.get("record_id") not in archive_record_ids
        ]
    )

    impact_core = {
        "confirmed_link_id": confirmed_link_id,
        "confirmed_link_sha256": link.get("confirmed_link_sha256"),
        "accepted_review_decision_id": link.get("accepted_review_decision_id"),
        "accepted_review_decision_sha256": link.get("accepted_review_decision_sha256"),
        "affected_case_ids": case_ids,
        "affected_entities": impacted_entities,
        "evidence_packages": evidence_packages,
        "review_queues": review_queues,
        "closure_states": closure_states,
        "archive_records": archive_records,
        "graph_node_ids": sorted(node.get("node_id") for node in impacted_nodes),
        "graph_edge_ids": sorted(edge.get("edge_id") for edge in impacted_edges),
    }
    category_counts = Counter(node.get("node_type") for node in impacted_entities)

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "ready",
        "access_scope": {
            "mode": "restricted"
            if allowed_case_ids is not None
            else "all_visible_cases",
            "allowed_case_ids": sorted(allowed_case_ids)
            if allowed_case_ids is not None
            else None,
        },
        "impact": impact_core,
        "impact_sha256": _sha(impact_core),
        "counts": {
            "affected_cases": len(case_ids),
            "affected_entities": len(impacted_entities),
            "entities_by_type": dict(sorted(category_counts.items())),
            "evidence_packages": len(evidence_packages),
            "review_queue_entries": len(review_queues),
            "closure_states": len(closure_states),
            "archive_records": len(archive_records),
            "graph_nodes": len(impacted_nodes),
            "graph_edges": len(impacted_edges),
        },
        "confirmed_link_binding": {
            "confirmed_link_id": link.get("confirmed_link_id"),
            "confirmed_link_sha256": link.get("confirmed_link_sha256"),
            "registry_record_id": link.get("registry_record_id"),
            "accepted_review_decision_id": link.get("accepted_review_decision_id"),
            "accepted_review_decision_sha256": link.get(
                "accepted_review_decision_sha256"
            ),
            "source_occurrences_sha256": link.get("source_occurrences_sha256"),
        },
        "graph_binding": {
            "graph_sha256": graph_payload.get("graph_sha256"),
            "graph_node_ids": impact_core["graph_node_ids"],
            "graph_edge_ids": impact_core["graph_edge_ids"],
        },
        "confirmed_link_mutated": False,
        "graph_mutated": False,
        "source_records_mutated": False,
        "impact_record_created": False,
        "next_action": "review_cross_case_link_impact",
    }
