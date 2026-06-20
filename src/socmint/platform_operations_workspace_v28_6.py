from __future__ import annotations

import os
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from . import database
from .platform_operations_events_v28_6 import (
    SCHEMA,
    VERSION,
    current_incidents,
    history,
)


def _iso(value: Any) -> str | None:
    return value.isoformat() if value else None


def _jobs(limit: int = 1000) -> list[dict[str, Any]]:
    database.ensure_configured()
    session = database.Session()
    try:
        rows = (
            session.query(database.ScanJob)
            .order_by(database.ScanJob.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "job_id": getattr(row, "id", None),
                "status": str(getattr(row, "status", None) or "unknown").lower(),
                "created_at": _iso(getattr(row, "created_at", None)),
                "updated_at": _iso(getattr(row, "updated_at", None)),
                "started_at": _iso(getattr(row, "started_at", None)),
                "completed_at": _iso(getattr(row, "completed_at", None)),
                "error_present": bool(getattr(row, "error", None)),
                "job_type": getattr(row, "job_type", None)
                or getattr(row, "scan_type", None),
            }
            for row in rows
        ]
    finally:
        session.close()


def _connector_runs(limit: int = 1000) -> list[dict[str, Any]]:
    database.ensure_configured()
    session = database.Session()
    try:
        rows = (
            session.query(database.ConnectorRun)
            .order_by(database.ConnectorRun.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "run_id": getattr(row, "id", None),
                "connector": str(getattr(row, "connector", None) or "unknown"),
                "status": str(getattr(row, "status", None) or "unknown").lower(),
                "created_at": _iso(getattr(row, "created_at", None)),
                "error_present": bool(getattr(row, "error", None)),
            }
            for row in rows
        ]
    finally:
        session.close()


def _audit_snapshot(limit: int = 2000) -> dict[str, Any]:
    database.ensure_configured()
    session = database.Session()
    try:
        rows = (
            session.query(database.AuditLog)
            .order_by(database.AuditLog.id.asc())
            .limit(limit)
            .all()
        )
        ids = [int(row.id) for row in rows if row.id is not None]
        gaps = []
        for left, right in zip(ids, ids[1:]):
            if right != left + 1:
                gaps.append(
                    {
                        "after_id": left,
                        "before_id": right,
                        "missing_count": right - left - 1,
                    }
                )
        action_counts = Counter(str(row.action or "unknown") for row in rows)
        actor_counts = Counter(str(row.actor or "unknown") for row in rows)
        return {
            "record_count": len(rows),
            "first_record_id": ids[0] if ids else None,
            "last_record_id": ids[-1] if ids else None,
            "id_gap_count": len(gaps),
            "id_gaps": gaps[:100],
            "action_counts": dict(sorted(action_counts.items())),
            "actor_counts": dict(sorted(actor_counts.items())),
            "latest_recorded_at": _iso(rows[-1].created_at) if rows else None,
        }
    finally:
        session.close()


def _configuration_state() -> dict[str, Any]:
    keys = (
        "DATABASE_URL",
        "SOCMINT_DATA_DIR",
        "SOCMINT_SECRET_KEY",
        "SOCMINT_AUTO_CREATE_DB",
        "SOCMINT_LOG_FILE",
    )
    return {
        "variables": {
            key: {"configured": bool(os.getenv(key)), "value_exposed": False}
            for key in keys
        },
        "secret_values_exposed": False,
        "configuration_mutated": False,
    }


def _storage_state() -> dict[str, Any]:
    raw = os.getenv("SOCMINT_DATA_DIR") or "."
    path = Path(raw)
    exists = path.exists()
    writable = bool(exists and os.access(path, os.W_OK))
    return {
        "path_configured": bool(raw),
        "path_exists": exists,
        "path_writable": writable,
        "path_value_exposed": False,
    }


def build_platform_operations_workspace(
    *, stale_after_hours: int = 24
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=max(1, int(stale_after_hours)))
    jobs = _jobs()
    connector_runs = _connector_runs()
    audit = _audit_snapshot()
    incidents = current_incidents()
    operational_events = history()

    job_counts = Counter(item["status"] for item in jobs)
    failed_jobs = [
        item
        for item in jobs
        if item["status"] in {"failed", "error", "blocked"} or item["error_present"]
    ]
    stalled_jobs = []
    for item in jobs:
        if item["status"] not in {"queued", "pending", "running", "in_progress"}:
            continue
        stamp = (
            item.get("updated_at") or item.get("started_at") or item.get("created_at")
        )
        try:
            parsed = (
                datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
                if stamp
                else None
            )
        except ValueError:
            parsed = None
        if parsed and parsed < cutoff:
            stalled_jobs.append(item)

    connector_status_counts = Counter(item["status"] for item in connector_runs)
    connector_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in connector_runs:
        connector_groups[item["connector"]].append(item)
    connector_continuity = []
    for name, items in sorted(connector_groups.items()):
        latest = items[0]
        connector_continuity.append(
            {
                "connector": name,
                "run_count": len(items),
                "latest_status": latest["status"],
                "latest_run_at": latest["created_at"],
                "error_count": sum(
                    item["error_present"] or item["status"] in {"failed", "error"}
                    for item in items
                ),
            }
        )

    database_ready = bool(database.check_ready())
    storage = _storage_state()
    configuration = _configuration_state()
    open_incidents = [
        item for item in incidents if item.get("incident_status") != "resolved"
    ]
    critical_open = sum(
        (item.get("definition") or {}).get("severity") == "critical"
        for item in open_incidents
    )
    findings = []
    if not database_ready:
        findings.append({"severity": "critical", "key": "database_not_ready"})
    if not storage["path_exists"] or not storage["path_writable"]:
        findings.append({"severity": "high", "key": "storage_not_ready"})
    if failed_jobs:
        findings.append(
            {
                "severity": "high",
                "key": "failed_jobs_present",
                "count": len(failed_jobs),
            }
        )
    if stalled_jobs:
        findings.append(
            {
                "severity": "high",
                "key": "stalled_jobs_present",
                "count": len(stalled_jobs),
            }
        )
    if audit["id_gap_count"]:
        findings.append(
            {
                "severity": "medium",
                "key": "audit_id_gaps_detected",
                "count": audit["id_gap_count"],
            }
        )
    if any(item["error_count"] for item in connector_continuity):
        findings.append({"severity": "medium", "key": "connector_run_errors_present"})
    if critical_open:
        findings.append(
            {
                "severity": "critical",
                "key": "critical_operational_incident_open",
                "count": critical_open,
            }
        )

    overall_status = "healthy"
    if any(item["severity"] == "critical" for item in findings):
        overall_status = "critical"
    elif any(item["severity"] == "high" for item in findings):
        overall_status = "attention_required"
    elif findings:
        overall_status = "degraded"

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "ready",
        "overall_status": overall_status,
        "database_health": {"ready": database_ready},
        "storage_health": storage,
        "configuration_state": configuration,
        "job_health": {
            "job_count": len(jobs),
            "status_counts": dict(sorted(job_counts.items())),
            "failed_jobs": failed_jobs,
            "failed_job_count": len(failed_jobs),
            "stalled_jobs": stalled_jobs,
            "stalled_job_count": len(stalled_jobs),
            "stale_after_hours": max(1, int(stale_after_hours)),
        },
        "connector_run_health": {
            "run_count": len(connector_runs),
            "status_counts": dict(sorted(connector_status_counts.items())),
            "continuity": connector_continuity,
        },
        "audit_log_continuity": audit,
        "operational_incidents": incidents,
        "open_operational_incidents": open_incidents,
        "operational_incident_count": len(incidents),
        "open_operational_incident_count": len(open_incidents),
        "operational_findings": findings,
        "operational_finding_count": len(findings),
        "operational_history": operational_events[-250:],
        "operational_event_count": len(operational_events),
        "job_execution_available": False,
        "service_restart_available": False,
        "configuration_mutation_available": False,
        "audit_log_mutation_available": False,
        "secret_values_visible": False,
        "case_access_scope_changed_by_view": False,
        "next_action": "review_platform_operations_and_incidents",
    }
