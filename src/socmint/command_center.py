from __future__ import annotations

import json
from collections import Counter
from typing import Any

from . import database as db
from .full_report_history import full_report_export_history

USERNAME_TOOLS = {"sherlock", "maigret", "social-analyzer", "social_analyzer"}
EMAIL_TOOLS = {"holehe", "h8mail", "emailrep", "breach", "email"}
PHONE_TOOLS = {"phoneinfoga", "phone", "numverify"}
URL_TOOLS = {"playwright", "exiftool", "metadata", "webcapture", "wayback"}


def _job_tools(job) -> list[str]:
    try:
        return list(json.loads(job.tools or "[]"))
    except Exception:
        return []


def tool_compatibility(target_type: str, tools: list[str]) -> dict[str, Any]:
    normalized = {tool.strip().lower() for tool in tools if tool.strip()}
    warnings = []
    suggestions = []
    compatible = True

    if target_type == "email" and normalized & USERNAME_TOOLS:
        compatible = False
        warnings.append(
            "Email targets do not work well with username-first tools such as Sherlock or Maigret."
        )
        suggestions.append("Use email exposure/account-discovery connectors for email targets.")
    if target_type in {"username", "handle"} and not normalized & USERNAME_TOOLS:
        suggestions.append("Username targets are usually best tested with Sherlock/Maigret-style tools.")
    if target_type == "phone" and not normalized & PHONE_TOOLS:
        suggestions.append("Phone targets need phone-specific enrichment tools.")
    if target_type in {"url", "domain"} and not normalized & URL_TOOLS:
        suggestions.append("URL/domain targets benefit from web capture and metadata connectors.")

    if not tools:
        suggestions.append("No tools selected. Choose tools matched to the seed type before running.")

    return {
        "compatible": compatible,
        "warnings": warnings,
        "suggestions": suggestions,
        "target_type": target_type,
        "tools": sorted(normalized),
    }


def _serialize_job(job) -> dict[str, Any]:
    tools = _job_tools(job)
    return {
        "id": job.id,
        "target": job.target_value,
        "target_type": job.target_type,
        "tools": tools,
        "enrich": bool(job.enrich),
        "status": job.status,
        "requested_by": job.requested_by,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "error": job.error,
        "target_id": job.target_id,
        "compatibility": tool_compatibility(job.target_type, tools),
    }


def _serialize_target(target) -> dict[str, Any]:
    return {
        "id": target.id,
        "value": target.value,
        "type": target.type,
        "created_at": target.created_at.isoformat() if target.created_at else None,
    }


def _serialize_subject(subject) -> dict[str, Any]:
    history = full_report_export_history(subject.id, limit=5)
    return {
        "id": subject.id,
        "label": subject.label or f"Subject {subject.id}",
        "created_at": subject.created_at.isoformat() if subject.created_at else None,
        "latest_report_available": bool(history.get("exports")),
        "latest_report_name": (history.get("exports") or [{}])[0].get("name"),
        "report_count": history.get("count", 0),
    }


def command_center_payload() -> dict[str, Any]:
    db.ensure_configured()
    session = db.Session()
    try:
        jobs = (
            session.query(db.ScanJob)
            .order_by(db.ScanJob.created_at.desc())
            .limit(25)
            .all()
        )
        targets = (
            session.query(db.Target)
            .order_by(db.Target.created_at.desc())
            .limit(10)
            .all()
        )
        subjects = (
            session.query(db.SpineSubject)
            .order_by(db.SpineSubject.created_at.desc())
            .limit(10)
            .all()
        )
        connector_runs = (
            session.query(db.SpineConnectorRun)
            .order_by(db.SpineConnectorRun.created_at.desc())
            .limit(10)
            .all()
        )
        findings_count = session.query(db.Finding).count()
        statuses = Counter(job.status for job in jobs)
        queued_count = statuses.get("queued", 0)
        running_count = statuses.get("running", 0)
        failed_jobs = [job for job in jobs if job.status == "failed"]
        completed_jobs = [job for job in jobs if job.status == "completed"]
        compatibility_warnings = [
            _serialize_job(job)
            for job in jobs
            if _serialize_job(job)["compatibility"]["warnings"]
        ]
        latest_processed = completed_jobs[0] if completed_jobs else None
        return {
            "schema": "socmint.command_center.v7_5_8",
            "summary": {
                "subject_count": len(subjects),
                "target_count": len(targets),
                "job_count": len(jobs),
                "queued_jobs": queued_count,
                "running_jobs": running_count,
                "failed_jobs": len(failed_jobs),
                "completed_jobs": len(completed_jobs),
                "spine_connector_runs": len(connector_runs),
                "findings_count": findings_count,
                "worker_hint": "Jobs are queued. Run Process queued jobs now or start process-jobs." if queued_count else "No queued jobs waiting.",
            },
            "subjects": [_serialize_subject(subject) for subject in subjects],
            "targets": [_serialize_target(target) for target in targets],
            "jobs": [_serialize_job(job) for job in jobs],
            "compatibility_warnings": compatibility_warnings,
            "latest_processed_job": _serialize_job(latest_processed) if latest_processed else None,
            "next_actions": [
                {"label": "Create / open subject", "href": "/spine", "priority": "primary"},
                {"label": "Review queued jobs", "href": "/jobs", "priority": "secondary"},
                {"label": "Open enrichment review", "href": "/spine/enrichment-review", "priority": "secondary"},
                {"label": "Open export center", "href": "/reports/export-center", "priority": "secondary"},
            ],
            "tool_guidance": [
                {"target_type": "username", "recommended": "Sherlock, Maigret, Social Analyzer"},
                {"target_type": "email", "recommended": "Holehe, h8mail, email exposure/account-discovery connectors"},
                {"target_type": "phone", "recommended": "PhoneInfoga or phone-specific enrichment"},
                {"target_type": "url/domain", "recommended": "Playwright capture, metadata extraction, web archive checks"},
            ],
        }
    finally:
        session.close()
