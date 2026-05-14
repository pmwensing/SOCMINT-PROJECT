from __future__ import annotations

import os
from collections import Counter
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import inspect

from . import database as db
from .build_scope_lock import evaluate_scope_lock
from .workbench import ALLOWED_JOB_TYPES

REQUIRED_V7_5_TABLES = [
    "spine_subjects",
    "spine_seeds",
    "spine_connector_runs",
    "spine_observations",
    "spine_dossier_assertions",
    "audit_logs",
    "policy_gate_events",
    "workbench_jobs",
    "dossier_exports",
]

REQUIRED_V7_5_ROUTES = [
    "/api/v1/spine/subjects/<int:subject_id>/full-report",
    "/api/v1/spine/subjects/<int:subject_id>/full-report/run",
    "/api/v1/spine/subjects/<int:subject_id>/full-report/latest",
    "/api/v1/workbench/scope-lock",
    "/api/v1/workbench/build-spec-lock",
]


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _safe_json(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        import json

        return json.loads(value)
    except Exception:
        return default


def _table_names() -> set[str]:
    db.ensure_configured()
    try:
        return set(inspect(db.engine).get_table_names())
    except Exception:
        return set()


def build_drift_report(app=None) -> dict[str, Any]:
    tables = _table_names()
    missing_tables = [name for name in REQUIRED_V7_5_TABLES if name not in tables]
    available_tables = [name for name in REQUIRED_V7_5_TABLES if name in tables]

    routes = sorted(str(rule.rule) for rule in app.url_map.iter_rules()) if app is not None else []
    route_set = set(routes)
    missing_routes = [rule for rule in REQUIRED_V7_5_ROUTES if rule not in route_set]
    available_routes = [rule for rule in REQUIRED_V7_5_ROUTES if rule in route_set]

    env_findings = []
    if os.environ.get("SECRET_KEY") and not os.environ.get("SOCMINT_SECRET_KEY"):
        env_findings.append(
            {
                "status": "warn",
                "key": "SOCMINT_SECRET_KEY",
                "detail": "SECRET_KEY is set but SOCMINT_SECRET_KEY is not. Current config expects SOCMINT_SECRET_KEY.",
            }
        )
    if not os.environ.get("SOCMINT_SECRET_KEY"):
        env_findings.append(
            {
                "status": "warn",
                "key": "SOCMINT_SECRET_KEY",
                "detail": "SOCMINT_SECRET_KEY is not present in the process environment.",
            }
        )
    if os.environ.get("DATABASE_URL", "").find("@db:") != -1:
        env_findings.append(
            {
                "status": "warn",
                "key": "DATABASE_URL",
                "detail": "DATABASE_URL references host db; Docker Compose for this repo commonly uses postgres.",
            }
        )

    status = "pass"
    if missing_tables or missing_routes:
        status = "fail"
    elif any(item["status"] == "warn" for item in env_findings):
        status = "warn"

    return {
        "schema": "socmint.v7_5.drift_report",
        "generated_at": utc_now(),
        "status": status,
        "approved_line": "v7.5",
        "available_tables": available_tables,
        "missing_tables": missing_tables,
        "available_routes": available_routes,
        "missing_routes": missing_routes,
        "allowed_workbench_job_types": sorted(ALLOWED_JOB_TYPES),
        "environment_findings": env_findings,
        "scope_lock": evaluate_scope_lock(app),
    }


def build_audit_report(app=None, limit: int = 100) -> dict[str, Any]:
    db.ensure_configured()
    audit_events = db.get_audit_events(limit=limit)
    try:
        policy_events = db.list_policy_gate_events(limit=limit)
    except Exception:
        policy_events = []
    try:
        jobs = db.list_workbench_jobs(limit=limit)
    except Exception:
        jobs = []

    audit_action_counts = Counter(event.action for event in audit_events)
    policy_action_counts = Counter(event.action for event in policy_events)
    job_status_counts = Counter(job.status for job in jobs)

    recent_audit = [
        {
            "id": event.id,
            "actor": event.actor,
            "action": event.action,
            "target_value": event.target_value,
            "ip_address": event.ip_address,
            "details": _safe_json(event.details, {}),
            "created_at": event.created_at.isoformat() if event.created_at else None,
        }
        for event in audit_events[:25]
    ]
    recent_policy = [
        {
            "id": event.id,
            "action": event.action,
            "allowed": bool(event.allowed),
            "reasons": _safe_json(event.reasons_json, []),
            "actor": event.actor,
            "created_at": event.created_at.isoformat() if event.created_at else None,
        }
        for event in policy_events[:25]
    ]

    return {
        "schema": "socmint.v7_5.audit_report",
        "generated_at": utc_now(),
        "status": "pass",
        "approved_line": "v7.5",
        "counts": {
            "audit_events": len(audit_events),
            "policy_events": len(policy_events),
            "workbench_jobs": len(jobs),
        },
        "audit_action_counts": dict(sorted(audit_action_counts.items())),
        "policy_action_counts": dict(sorted(policy_action_counts.items())),
        "job_status_counts": dict(sorted(job_status_counts.items())),
        "recent_audit_events": recent_audit,
        "recent_policy_events": recent_policy,
        "drift": build_drift_report(app),
    }
