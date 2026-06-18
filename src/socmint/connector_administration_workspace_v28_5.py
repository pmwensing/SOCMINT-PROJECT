from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

from . import database
from .connector_administration_events_v28_5 import AUTH_STATES, SCHEMA, VERSION, current_connectors, history


def _run_health() -> dict[str, dict[str, Any]]:
    database.ensure_configured()
    session = database.Session()
    try:
        rows = session.query(database.ConnectorRun).order_by(database.ConnectorRun.created_at.desc()).limit(1000).all()
        grouped: dict[str, list[Any]] = defaultdict(list)
        for row in rows:
            grouped[str(getattr(row, "connector", None) or "unknown")].append(row)
        result = {}
        for name, items in grouped.items():
            statuses = Counter(str(getattr(item, "status", None) or "unknown").lower() for item in items)
            latest = items[0]
            result[name] = {
                "run_count": len(items),
                "status_counts": dict(sorted(statuses.items())),
                "latest_status": getattr(latest, "status", None),
                "latest_run_at": latest.created_at.isoformat() if getattr(latest, "created_at", None) else None,
                "error_count": sum(bool(getattr(item, "error", None)) for item in items),
            }
        return result
    finally:
        session.close()


def _parse_time(value: Any):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def build_connector_administration_workspace() -> dict[str, Any]:
    connectors = current_connectors()
    active = [item for item in connectors if item.get("connector_status") == "active"]
    disabled = [item for item in connectors if item.get("connector_status") == "disabled"]
    health = _run_health()
    findings = []
    now = datetime.now(timezone.utc)
    summaries = []
    for item in connectors:
        definition = item.get("definition") or {}
        name = str(definition.get("name") or "")
        readiness = str(item.get("auth_readiness") or "not_configured")
        expires_at = _parse_time(item.get("auth_expires_at"))
        if item.get("enabled") and readiness not in {"configured", "expiring"}:
            findings.append({"severity":"high","key":"enabled_connector_not_auth_ready","connector_id":item.get("connector_id"),"auth_readiness":readiness})
        if expires_at and expires_at < now:
            findings.append({"severity":"high","key":"connector_auth_expired","connector_id":item.get("connector_id"),"auth_expires_at":expires_at.isoformat()})
        if not (definition.get("authorization_scopes") or []):
            findings.append({"severity":"medium","key":"connector_without_authorization_scope","connector_id":item.get("connector_id")})
        if not (definition.get("rate_limit_policy") or {}):
            findings.append({"severity":"low","key":"connector_without_rate_limit_policy","connector_id":item.get("connector_id")})
        run_state = health.get(name, {"run_count":0,"status_counts":{},"latest_status":None,"latest_run_at":None,"error_count":0})
        if run_state.get("error_count"):
            findings.append({"severity":"medium","key":"connector_run_errors","connector_id":item.get("connector_id"),"error_count":run_state.get("error_count")})
        summaries.append({
            "connector_id": item.get("connector_id"),
            "name": name,
            "connector_type": definition.get("connector_type"),
            "description": definition.get("description"),
            "authorization_scopes": definition.get("authorization_scopes") or [],
            "rate_limit_policy": definition.get("rate_limit_policy") or {},
            "enabled": bool(item.get("enabled")),
            "connector_status": item.get("connector_status"),
            "auth_readiness": readiness,
            "auth_expires_at": item.get("auth_expires_at"),
            "revision": item.get("revision"),
            "run_health": run_state,
            "secret_values_exposed": False,
        })
    events = history()
    readiness_counts = Counter(str(item.get("auth_readiness") or "not_configured") for item in connectors if item.get("connector_status") != "superseded")
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "ready",
        "connectors": connectors,
        "connector_summaries": summaries,
        "connector_count": len(connectors),
        "active_connector_count": len(active),
        "disabled_connector_count": len(disabled),
        "auth_readiness_states": list(AUTH_STATES),
        "auth_readiness_counts": dict(sorted(readiness_counts.items())),
        "connector_health": health,
        "administration_findings": findings,
        "administration_finding_count": len(findings),
        "connector_history": events[-250:],
        "connector_event_count": len(events),
        "secret_values_visible": False,
        "raw_connector_commands_visible": False,
        "raw_connector_results_visible": False,
        "connector_execution_available": False,
        "case_access_scope_changed_by_view": False,
        "next_action": "review_connector_and_integration_state",
    }
