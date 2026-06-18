from __future__ import annotations

from collections import Counter, defaultdict
from datetime import timedelta
from typing import Any

from . import database
from .dossier_assembly_workspace_v21_0 import _ensure_storage, _json_details, _sha

SCHEMA = "socmint.administration_workspace.v28_0"
VERSION = "v28.0.0"

TEAM_ACTION_MARKERS = ("team", "membership", "supervisor")
ACCESS_ACTION_MARKERS = ("access", "permission", "grant", "role_assignment", "role_revocation")
POLICY_ACTION_MARKERS = ("policy", "governance", "certification", "compliance")
SESSION_ACTION_MARKERS = ("login", "logout", "session", "authentication")
ADMIN_ACTION_MARKERS = TEAM_ACTION_MARKERS + ACCESS_ACTION_MARKERS + POLICY_ACTION_MARKERS + SESSION_ACTION_MARKERS + ("user_", "connector_")
OPEN_STATES = {"pending", "requested", "open", "overdue", "blocked", "failed", "requires_review"}


def _events(limit: int = 500) -> list[dict[str, Any]]:
    _ensure_storage()
    session = database.Session()
    try:
        rows = session.query(database.AuditLog).order_by(database.AuditLog.created_at.desc(), database.AuditLog.id.desc()).limit(limit).all()
        return [{"record_id": row.id, "actor": row.actor, "action": row.action, "target_value": row.target_value, "ip_address": row.ip_address, "occurred_at": row.created_at.isoformat() if row.created_at else None, "created_at": row.created_at, "details": _json_details(row)} for row in rows]
    finally:
        session.close()


def _users() -> list[dict[str, Any]]:
    database.ensure_configured()
    session = database.Session()
    try:
        rows = session.query(database.User).order_by(database.User.username.asc()).all()
        return [{"user_id": row.id, "username": row.username, "role": row.role, "is_admin": bool(row.is_admin), "is_active": bool(row.is_active), "created_at": row.created_at.isoformat() if row.created_at else None} for row in rows]
    finally:
        session.close()


def _connectors() -> list[dict[str, Any]]:
    database.ensure_configured()
    session = database.Session()
    try:
        rows = session.query(database.ConnectorRun).order_by(database.ConnectorRun.created_at.desc(), database.ConnectorRun.id.desc()).limit(1000).all()
        grouped: dict[str, list[Any]] = defaultdict(list)
        for row in rows:
            grouped[str(row.connector or "unknown")].append(row)
        result = []
        for name, items in sorted(grouped.items()):
            statuses = Counter(str(item.status or "unknown").lower() for item in items)
            latest = items[0]
            result.append({"connector": name, "run_count": len(items), "status_counts": dict(sorted(statuses.items())), "latest_status": latest.status, "latest_run_at": latest.created_at.isoformat() if latest.created_at else None, "error_count": sum(1 for item in items if item.error), "credentials_exposed": False})
        return result
    finally:
        session.close()


def _jobs() -> dict[str, Any]:
    database.ensure_configured()
    session = database.Session()
    try:
        rows = session.query(database.ScanJob).order_by(database.ScanJob.created_at.desc()).limit(1000).all()
        counts = Counter(str(row.status or "unknown").lower() for row in rows)
        return {"job_count": len(rows), "status_counts": dict(sorted(counts.items())), "queued_count": counts.get("queued", 0), "running_count": counts.get("running", 0), "failed_count": counts.get("failed", 0)}
    finally:
        session.close()


def _contains(action: str, markers: tuple[str, ...]) -> bool:
    value = action.lower()
    return any(marker in value for marker in markers)


def build_administration_workspace(*, events: list[dict[str, Any]] | None = None, users: list[dict[str, Any]] | None = None, connectors: list[dict[str, Any]] | None = None, jobs: dict[str, Any] | None = None, session_window_hours: int = 24) -> dict[str, Any]:
    source_events = events if events is not None else _events()
    user_rows = users if users is not None else _users()
    connector_rows = connectors if connectors is not None else _connectors()
    job_state = jobs if jobs is not None else _jobs()

    role_counts = Counter(str(item.get("role") or "unassigned") for item in user_rows)
    user_summary = {"total": len(user_rows), "active": sum(bool(item.get("is_active")) for item in user_rows), "inactive": sum(not bool(item.get("is_active")) for item in user_rows), "administrators": sum(bool(item.get("is_admin")) for item in user_rows), "users": user_rows}
    role_summary = {"role_counts": dict(sorted(role_counts.items())), "distinct_role_count": len(role_counts), "least_privilege_review_required": any(role == "admin" and count > 1 for role, count in role_counts.items())}

    team_events = [item for item in source_events if _contains(str(item.get("action") or ""), TEAM_ACTION_MARKERS)]
    access_events = [item for item in source_events if _contains(str(item.get("action") or ""), ACCESS_ACTION_MARKERS)]
    policy_events = [item for item in source_events if _contains(str(item.get("action") or ""), POLICY_ACTION_MARKERS)]
    session_events = [item for item in source_events if _contains(str(item.get("action") or ""), SESSION_ACTION_MARKERS)]
    governance_events = [item for item in source_events if _contains(str(item.get("action") or ""), ADMIN_ACTION_MARKERS)]

    latest_session_by_actor: dict[str, dict[str, Any]] = {}
    for item in reversed(session_events):
        actor = str(item.get("actor") or "").strip()
        if actor:
            latest_session_by_actor[actor] = item
    active_sessions = []
    cutoff = database.utc_now() - timedelta(hours=max(1, int(session_window_hours)))
    for actor, item in sorted(latest_session_by_actor.items()):
        action = str(item.get("action") or "").lower()
        created_at = item.get("created_at")
        if "logout" not in action and created_at and created_at >= cutoff:
            active_sessions.append({"actor": actor, "last_action": item.get("action"), "last_seen_at": item.get("occurred_at"), "ip_address": item.get("ip_address"), "source_record_id": item.get("record_id")})

    def event_summary(items: list[dict[str, Any]], category: str) -> dict[str, Any]:
        return {"category": category, "event_count": len(items), "action_counts": dict(sorted(Counter(str(item.get("action") or "unknown") for item in items).items())), "latest_events": items[:25]}

    pending = []
    for item in governance_events:
        details = item.get("details") or {}
        state = str(details.get("status") or details.get("state") or "").lower()
        if state in OPEN_STATES:
            pending.append({"action": item.get("action"), "actor": item.get("actor"), "target_value": item.get("target_value"), "status": state, "reason": details.get("reason"), "due_at": details.get("due_at"), "source_record_id": item.get("record_id"), "occurred_at": item.get("occurred_at")})

    connector_status_counts = Counter(str(item.get("latest_status") or "unknown").lower() for item in connector_rows)
    connector_summary = {"connector_count": len(connector_rows), "healthy_count": sum(status in {"success", "completed", "ready", "passed"} for status in connector_status_counts.elements()), "failed_count": sum(status in {"failed", "error", "blocked"} for status in connector_status_counts.elements()), "connectors": connector_rows, "secrets_exposed": False}
    database_ready = bool(database.check_ready())
    system_health = {"database_ready": database_ready, "jobs": job_state, "connector_failures": connector_summary["failed_count"], "overall_status": "healthy" if database_ready and not job_state.get("failed_count") and not connector_summary["failed_count"] else "attention_required"}
    core = {"users": user_summary, "roles": role_summary, "teams": len(team_events), "access": len(access_events), "policies": len(policy_events), "connectors": connector_summary, "health": system_health, "pending": pending}
    return {"schema": SCHEMA, "version": VERSION, "status": "ready", "user_summary": user_summary, "role_summary": role_summary, "team_summary": event_summary(team_events, "team"), "active_sessions": active_sessions, "active_session_count": len(active_sessions), "access_grant_summary": event_summary(access_events, "access"), "policy_summary": event_summary(policy_events, "policy"), "connector_summary": connector_summary, "system_health": system_health, "pending_admin_actions": pending, "pending_admin_action_count": len(pending), "recent_governance_events": governance_events[:50], "governance_event_count": len(governance_events), "access_scope": {"mode": "administrative_read_only", "secrets_visible": False, "mutations_allowed": False}, "workspace_sha256": _sha(core), "read_only": True, "source_records_mutated": False, "user_records_mutated": False, "permission_records_mutated": False, "connector_records_mutated": False, "case_access_scope_changed": False, "next_action": "review_administration_state"}
