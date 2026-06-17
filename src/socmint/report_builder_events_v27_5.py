from __future__ import annotations

from typing import Any

from . import database
from .dossier_assembly_workspace_v21_0 import _canonical, _ensure_storage, _json_details, _sha

SCHEMA = "socmint.report_builder_export_packages.v27_5"
VERSION = "v27.5.0"
CREATE_ACTION = "search_report_definition_created"
REVISE_ACTION = "search_report_definition_revised"
GENERATE_ACTION = "search_report_package_generated"
ACTIONS = (CREATE_ACTION, REVISE_ACTION, GENERATE_ACTION)
VISIBILITIES = ("private", "shared")
EXPORT_FORMATS = ("json", "csv", "html")
SECTION_TYPES = ("saved_view", "watchlist", "text")


def blocked(key: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key}],
        "source_records_mutated": False,
        "case_access_scope_changed": False,
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
                "action_record_id": row.id,
                "recorded_by": row.actor,
                "recorded_at": row.created_at.isoformat() if row.created_at else None,
                "source_action": row.action,
            }
            for row in rows
        ]
    finally:
        session.close()


def current_reports() -> list[dict[str, Any]]:
    reports: dict[str, dict[str, Any]] = {}
    for event in history():
        report_id = str(event.get("report_id") or "")
        if event.get("event_type") in {"created", "revised"} and report_id:
            previous = str(event.get("supersedes_report_id") or "")
            if previous in reports:
                reports[previous] = {**reports[previous], "report_status": "superseded", "superseded_by_report_id": report_id}
            reports[report_id] = {**event, "report_status": "active"}
    return sorted(reports.values(), key=lambda item: (str(item.get("owner") or ""), str(item.get("name") or "")))


def visible_reports(user: str) -> list[dict[str, Any]]:
    return [item for item in current_reports() if item.get("owner") == user or item.get("visibility") == "shared"]


def find_report(report_id: str, user: str) -> dict[str, Any] | None:
    return next((item for item in visible_reports(user) if item.get("report_id") == report_id), None)


def _record(action: str, event: dict[str, Any], actor: str, ip: str | None) -> dict[str, Any]:
    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=actor,
            action=action,
            target_value=str(event.get("report_id") or event.get("package_id") or ""),
            ip_address=ip,
            details=_canonical(event),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return {**event, "action_record_id": row.id, "recorded_by": actor, "recorded_at": row.created_at.isoformat() if row.created_at else None}
    finally:
        session.close()


def _normalize_sections(sections: Any) -> list[dict[str, Any]] | None:
    if not isinstance(sections, list) or not sections:
        return None
    normalized = []
    for index, item in enumerate(sections, start=1):
        if not isinstance(item, dict):
            return None
        section_type = str(item.get("section_type") or "").strip()
        title = str(item.get("title") or "").strip()
        if section_type not in SECTION_TYPES or not title:
            return None
        source_id = str(item.get("source_id") or "").strip()
        text = str(item.get("text") or "").strip()
        if section_type in {"saved_view", "watchlist"} and not source_id:
            return None
        if section_type == "text" and not text:
            return None
        normalized.append({
            "position": index,
            "section_type": section_type,
            "title": title,
            "source_id": source_id or None,
            "text": text or None,
            "include_summary": item.get("include_summary") is not False,
            "include_results": item.get("include_results") is not False,
        })
    return normalized


def _duplicate(name: str, owner: str, exclude_id: str | None = None) -> bool:
    key = name.strip().lower()
    return any(
        item.get("owner") == owner
        and str(item.get("name") or "").strip().lower() == key
        and item.get("report_status") == "active"
        and item.get("report_id") != exclude_id
        for item in current_reports()
    )


def create_report_definition(
    *, name: str, owner: str, description: str, visibility: str,
    sections: Any, export_formats: Any, confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    name = str(name or "").strip()
    owner = str(owner or "").strip()
    visibility = str(visibility or "private").strip()
    formats = sorted({str(item) for item in (export_formats or []) if str(item) in EXPORT_FORMATS})
    normalized = _normalize_sections(sections)
    if confirmed is not True: return blocked("explicit_report_confirmation_required")
    if not name: return blocked("report_name_required")
    if not owner: return blocked("report_owner_required")
    if visibility not in VISIBILITIES: return blocked("report_visibility_invalid")
    if not normalized: return blocked("valid_report_sections_required")
    if not formats: return blocked("report_export_format_required")
    if _duplicate(name, owner): return blocked("active_report_name_must_be_unique_per_owner")
    definition = {"description": str(description or "").strip(), "sections": normalized, "export_formats": formats}
    content = {
        "event_type": "created", "name": name, "owner": owner, "visibility": visibility,
        "definition": definition, "definition_sha256": _sha(definition), "revision": 1,
        "supersedes_report_id": None,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA, "version": VERSION, **content,
        "report_id": f"report-{digest[:24]}",
        "report_event_id": f"report-event-{digest[:24]}",
        "report_event_sha256": digest,
        "source_records_mutated": False, "case_access_scope_changed": False,
        "report_grants_access": False,
    }
    return {**_record(CREATE_ACTION, event, owner, ip_address), "status": "report_definition_created", "next_action": "generate_report_package"}


def revise_report_definition(
    report_id: str, *, actor: str, name: str, description: str, visibility: str,
    sections: Any, export_formats: Any, reason: str, confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    previous = find_report(report_id, actor)
    if previous is None: return blocked("report_definition_required")
    if previous.get("owner") != actor: return blocked("report_owner_required")
    if previous.get("report_status") != "active": return blocked("active_report_required")
    if confirmed is not True: return blocked("explicit_report_revision_confirmation_required")
    reason = str(reason or "").strip()
    if not reason: return blocked("report_revision_reason_required")
    name = str(name or "").strip()
    visibility = str(visibility or "private").strip()
    formats = sorted({str(item) for item in (export_formats or []) if str(item) in EXPORT_FORMATS})
    normalized = _normalize_sections(sections)
    if not name: return blocked("report_name_required")
    if visibility not in VISIBILITIES: return blocked("report_visibility_invalid")
    if not normalized: return blocked("valid_report_sections_required")
    if not formats: return blocked("report_export_format_required")
    if _duplicate(name, actor, report_id): return blocked("active_report_name_must_be_unique_per_owner")
    definition = {"description": str(description or "").strip(), "sections": normalized, "export_formats": formats}
    binding = {"report_id": report_id, "report_event_id": previous.get("report_event_id"), "report_event_sha256": previous.get("report_event_sha256"), "definition_sha256": previous.get("definition_sha256"), "revision": previous.get("revision")}
    content = {
        "event_type": "revised", "name": name, "owner": actor, "visibility": visibility,
        "definition": definition, "definition_sha256": _sha(definition),
        "revision": int(previous.get("revision") or 1) + 1, "reason": reason,
        "supersedes_report_id": report_id, "previous_report_binding": binding,
        "previous_report_binding_sha256": _sha(binding),
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA, "version": VERSION, **content,
        "report_id": f"report-{digest[:24]}", "report_event_id": f"report-event-{digest[:24]}",
        "report_event_sha256": digest, "source_records_mutated": False,
        "prior_report_mutated": False, "case_access_scope_changed": False,
        "report_grants_access": False,
    }
    return {**_record(REVISE_ACTION, event, actor, ip_address), "status": "report_definition_revised", "next_action": "generate_report_package"}
