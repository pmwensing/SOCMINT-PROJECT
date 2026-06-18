from __future__ import annotations

from typing import Any

from . import database
from .dossier_assembly_workspace_v21_0 import _canonical, _ensure_storage, _json_details, _sha

SCHEMA = "socmint.team_organizational_structure.v28_3"
VERSION = "v28.3.0"
ACTIONS = (
    "administration_team_created",
    "administration_team_revised",
    "administration_team_member_added",
    "administration_team_member_removed",
    "administration_team_supervisor_assigned",
    "administration_team_scope_bound",
    "administration_team_workload_group_set",
)


def blocked(key: str) -> dict[str, Any]:
    return {"schema": SCHEMA, "version": VERSION, "status": "blocked", "blockers": [{"key": key}], "team_records_mutated": False, "case_access_scope_changed": False}


def history() -> list[dict[str, Any]]:
    _ensure_storage()
    session = database.Session()
    try:
        rows = session.query(database.AuditLog).filter(database.AuditLog.action.in_(ACTIONS)).order_by(database.AuditLog.created_at.asc(), database.AuditLog.id.asc()).all()
        return [{**_json_details(row), "audit_record_id": row.id, "actor": row.actor, "source_action": row.action, "target_value": row.target_value, "recorded_at": row.created_at.isoformat() if row.created_at else None} for row in rows]
    finally:
        session.close()


def _record(action: str, actor: str, target: str, event: dict[str, Any], ip_address: str | None) -> dict[str, Any]:
    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(actor=actor, action=action, target_value=target, ip_address=ip_address, details=_canonical(event))
        session.add(row)
        session.commit()
        session.refresh(row)
        return {**event, "audit_record_id": row.id, "actor": actor, "source_action": action, "target_value": target, "recorded_at": row.created_at.isoformat() if row.created_at else None}
    finally:
        session.close()


def current_teams() -> list[dict[str, Any]]:
    teams: dict[str, dict[str, Any]] = {}
    for event in history():
        event_type = event.get("event_type")
        team_id = str(event.get("team_id") or "")
        if not team_id:
            continue
        if event_type in {"team_created", "team_revised"}:
            previous = str(event.get("supersedes_team_id") or "")
            if previous in teams:
                teams[previous] = {**teams[previous], "team_status": "superseded", "superseded_by_team_id": team_id}
            teams[team_id] = {**event, "team_status": "active"}
        elif team_id in teams:
            team = dict(teams[team_id])
            if event_type == "team_member_added":
                members = set(team.get("member_usernames") or [])
                members.add(str(event.get("username") or ""))
                team["member_usernames"] = sorted(item for item in members if item)
            elif event_type == "team_member_removed":
                members = set(team.get("member_usernames") or [])
                members.discard(str(event.get("username") or ""))
                team["member_usernames"] = sorted(members)
            elif event_type == "team_supervisor_assigned":
                team["supervisor_username"] = event.get("supervisor_username")
            elif event_type == "team_scope_bound":
                team["organizational_scope"] = event.get("organizational_scope")
                team["ownership_boundaries"] = event.get("ownership_boundaries") or []
            elif event_type == "team_workload_group_set":
                team["workload_group"] = event.get("workload_group")
            teams[team_id] = team
    return sorted(teams.values(), key=lambda item: str((item.get("definition") or {}).get("name") or ""))


def find_team(team_id: str) -> dict[str, Any] | None:
    return next((item for item in current_teams() if item.get("team_id") == team_id), None)


def create_team(*, actor: str, name: str, description: str, reason: str, confirmed: bool, ip_address: str | None = None) -> dict[str, Any]:
    name, reason = str(name or "").strip(), str(reason or "").strip()
    if confirmed is not True: return blocked("explicit_team_creation_confirmation_required")
    if not name: return blocked("team_name_required")
    if not reason: return blocked("administrative_reason_required")
    if name.lower() in {str((item.get("definition") or {}).get("name") or "").lower() for item in current_teams() if item.get("team_status") == "active"}: return blocked("active_team_name_must_be_unique")
    definition = {"name": name, "description": str(description or "").strip()}
    content = {"event_type":"team_created","definition":definition,"definition_sha256":_sha(definition),"reason":reason,"revision":1,"supersedes_team_id":None,"member_usernames":[],"supervisor_username":None,"organizational_scope":None,"ownership_boundaries":[],"workload_group":None}
    digest = _sha(content)
    event = {"schema":SCHEMA,"version":VERSION,**content,"team_id":f"team-{digest[:24]}","team_event_id":f"team-event-{digest[:24]}","team_event_sha256":digest,"team_records_mutated":False,"case_access_scope_changed":False}
    return {**_record(ACTIONS[0], actor, name, event, ip_address), "status":"team_created", "next_action":"configure_team_structure"}


def revise_team(team_id: str, *, actor: str, name: str, description: str, reason: str, confirmed: bool, ip_address: str | None = None) -> dict[str, Any]:
    previous = find_team(team_id)
    if previous is None or previous.get("team_status") != "active": return blocked("active_team_required")
    if confirmed is not True: return blocked("explicit_team_revision_confirmation_required")
    if not str(reason or "").strip(): return blocked("administrative_reason_required")
    definition = {"name":str(name or (previous.get("definition") or {}).get("name") or "").strip(),"description":str(description or "").strip()}
    binding = {"team_id":team_id,"team_event_id":previous.get("team_event_id"),"team_event_sha256":previous.get("team_event_sha256"),"definition_sha256":previous.get("definition_sha256"),"revision":previous.get("revision")}
    content = {"event_type":"team_revised","definition":definition,"definition_sha256":_sha(definition),"reason":str(reason).strip(),"revision":int(previous.get("revision") or 1)+1,"supersedes_team_id":team_id,"previous_team_binding":binding,"previous_team_binding_sha256":_sha(binding),"member_usernames":previous.get("member_usernames") or [],"supervisor_username":previous.get("supervisor_username"),"organizational_scope":previous.get("organizational_scope"),"ownership_boundaries":previous.get("ownership_boundaries") or [],"workload_group":previous.get("workload_group")}
    digest = _sha(content)
    event = {"schema":SCHEMA,"version":VERSION,**content,"team_id":f"team-{digest[:24]}","team_event_id":f"team-event-{digest[:24]}","team_event_sha256":digest,"prior_team_event_mutated":False,"case_access_scope_changed":False}
    return {**_record(ACTIONS[1], actor, definition["name"], event, ip_address), "status":"team_revised", "next_action":"review_team_structure"}


def append_team_event(team_id: str, *, actor: str, event_type: str, reason: str, confirmed: bool, ip_address: str | None = None, **fields: Any) -> dict[str, Any]:
    team = find_team(team_id)
    if team is None or team.get("team_status") != "active": return blocked("active_team_required")
    if confirmed is not True: return blocked("explicit_team_change_confirmation_required")
    if not str(reason or "").strip(): return blocked("administrative_reason_required")
    action_map = {"team_member_added":ACTIONS[2],"team_member_removed":ACTIONS[3],"team_supervisor_assigned":ACTIONS[4],"team_scope_bound":ACTIONS[5],"team_workload_group_set":ACTIONS[6]}
    if event_type not in action_map: return blocked("team_event_type_invalid")
    content = {"event_type":event_type,"team_id":team_id,"reason":str(reason).strip(),**fields}
    digest = _sha(content)
    event = {"schema":SCHEMA,"version":VERSION,**content,"team_event_id":f"team-event-{digest[:24]}","team_event_sha256":digest,"team_membership_grants_case_access":False,"case_access_scope_changed":False}
    return {**_record(action_map[event_type], actor, team_id, event, ip_address), "status":"team_updated", "next_action":"review_team_structure"}
