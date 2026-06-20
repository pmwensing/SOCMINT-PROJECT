from __future__ import annotations

from typing import Any

from . import database
from .dossier_assembly_workspace_v21_0 import (
    _canonical,
    _ensure_storage,
    _json_details,
    _sha,
)

SCHEMA = "socmint.platform_health_jobs_operational_audit.v28_6"
VERSION = "v28.6.0"
ACTIONS = (
    "administration_operational_incident_opened",
    "administration_operational_incident_acknowledged",
    "administration_operational_incident_resolved",
)
SEVERITIES = ("low", "medium", "high", "critical")


def blocked(key: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key}],
        "job_execution_performed": False,
        "configuration_mutated": False,
        "audit_records_mutated": False,
    }


def history() -> list[dict[str, Any]]:
    _ensure_storage()
    session = database.Session()
    try:
        rows = (
            session.query(database.AuditLog)
            .filter(database.AuditLog.action.in_(ACTIONS))
            .order_by(database.AuditLog.created_at.asc(), database.AuditLog.id.asc())
            .all()
        )
        return [
            {
                **_json_details(row),
                "audit_record_id": row.id,
                "actor": row.actor,
                "source_action": row.action,
                "target_value": row.target_value,
                "recorded_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    finally:
        session.close()


def _record(
    action: str, actor: str, target: str, event: dict[str, Any], ip_address: str | None
) -> dict[str, Any]:
    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=actor,
            action=action,
            target_value=target,
            ip_address=ip_address,
            details=_canonical(event),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return {
            **event,
            "audit_record_id": row.id,
            "actor": actor,
            "source_action": action,
            "target_value": target,
            "recorded_at": row.created_at.isoformat() if row.created_at else None,
        }
    finally:
        session.close()


def current_incidents() -> list[dict[str, Any]]:
    incidents: dict[str, dict[str, Any]] = {}
    for event in history():
        incident_id = str(event.get("incident_id") or "")
        if not incident_id:
            continue
        event_type = event.get("event_type")
        if event_type == "incident_opened":
            incidents[incident_id] = {
                **event,
                "incident_status": "open",
                "acknowledgements": [],
            }
        elif incident_id in incidents:
            incident = dict(incidents[incident_id])
            if event_type == "incident_acknowledged":
                incident["incident_status"] = "acknowledged"
                incident["acknowledgements"] = [
                    *incident.get("acknowledgements", []),
                    event,
                ]
            elif event_type == "incident_resolved":
                incident["incident_status"] = "resolved"
                incident["resolution_event"] = event
            incidents[incident_id] = incident
    return sorted(
        incidents.values(),
        key=lambda item: str(item.get("recorded_at") or ""),
        reverse=True,
    )


def find_incident(incident_id: str) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in current_incidents()
            if item.get("incident_id") == incident_id
        ),
        None,
    )


def open_incident(
    *,
    actor: str,
    title: str,
    severity: str,
    component: str,
    description: str,
    source_binding: Any,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    title = str(title or "").strip()
    severity = str(severity or "").strip()
    component = str(component or "").strip()
    reason = str(reason or "").strip()
    binding = source_binding if isinstance(source_binding, dict) else {}
    if confirmed is not True:
        return blocked("explicit_incident_creation_confirmation_required")
    if not title:
        return blocked("incident_title_required")
    if severity not in SEVERITIES:
        return blocked("incident_severity_invalid")
    if not component:
        return blocked("incident_component_required")
    if not reason:
        return blocked("administrative_reason_required")
    definition = {
        "title": title,
        "severity": severity,
        "component": component,
        "description": str(description or "").strip(),
        "source_binding": binding,
    }
    content = {
        "event_type": "incident_opened",
        "definition": definition,
        "definition_sha256": _sha(definition),
        "reason": reason,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "incident_id": f"operational-incident-{digest[:24]}",
        "incident_event_id": f"incident-event-{digest[:24]}",
        "incident_event_sha256": digest,
        "job_execution_performed": False,
        "configuration_mutated": False,
        "audit_records_mutated": False,
    }
    result = _record(ACTIONS[0], actor, title, event, ip_address)
    return {
        **result,
        "status": "operational_incident_opened",
        "next_action": "acknowledge_operational_incident",
    }


def acknowledge_incident(
    incident_id: str,
    *,
    actor: str,
    note: str,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    incident = find_incident(incident_id)
    if incident is None or incident.get("incident_status") == "resolved":
        return blocked("active_operational_incident_required")
    if confirmed is not True:
        return blocked("explicit_incident_acknowledgement_confirmation_required")
    reason = str(reason or "").strip()
    if not reason:
        return blocked("administrative_reason_required")
    binding = {
        "incident_id": incident_id,
        "incident_event_id": incident.get("incident_event_id"),
        "incident_event_sha256": incident.get("incident_event_sha256"),
    }
    content = {
        "event_type": "incident_acknowledged",
        "incident_id": incident_id,
        "note": str(note or "").strip(),
        "reason": reason,
        "incident_binding": binding,
        "incident_binding_sha256": _sha(binding),
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "incident_event_id": f"incident-event-{digest[:24]}",
        "incident_event_sha256": digest,
        "job_execution_performed": False,
        "configuration_mutated": False,
        "audit_records_mutated": False,
    }
    result = _record(ACTIONS[1], actor, incident_id, event, ip_address)
    return {
        **result,
        "status": "operational_incident_acknowledged",
        "next_action": "resolve_operational_incident",
    }


def resolve_incident(
    incident_id: str,
    *,
    actor: str,
    resolution: str,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    incident = find_incident(incident_id)
    if incident is None or incident.get("incident_status") == "resolved":
        return blocked("active_operational_incident_required")
    if confirmed is not True:
        return blocked("explicit_incident_resolution_confirmation_required")
    resolution = str(resolution or "").strip()
    reason = str(reason or "").strip()
    if not resolution:
        return blocked("incident_resolution_required")
    if not reason:
        return blocked("administrative_reason_required")
    binding = {
        "incident_id": incident_id,
        "incident_event_id": incident.get("incident_event_id"),
        "incident_event_sha256": incident.get("incident_event_sha256"),
    }
    content = {
        "event_type": "incident_resolved",
        "incident_id": incident_id,
        "resolution": resolution,
        "reason": reason,
        "incident_binding": binding,
        "incident_binding_sha256": _sha(binding),
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "incident_event_id": f"incident-event-{digest[:24]}",
        "incident_event_sha256": digest,
        "job_execution_performed": False,
        "configuration_mutated": False,
        "audit_records_mutated": False,
    }
    result = _record(ACTIONS[2], actor, incident_id, event, ip_address)
    return {
        **result,
        "status": "operational_incident_resolved",
        "next_action": "review_operational_history",
    }
