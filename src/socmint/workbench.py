import json
import os
from datetime import datetime, UTC

from . import database as db


ALLOWED_JOB_TYPES = {
    "spine_run",
    "media_profile_enrichment",
    "contradiction_detection",
    "dossier_export",
    "full_dossier_pipeline",
}

DEFAULT_RETENTION_DAYS = 180


def _json_loads(value, default=None):
    if default is None:
        default = {}
    try:
        return json.loads(value or "{}")
    except json.JSONDecodeError:
        return default


def evaluate_policy(action: str, payload: dict | None = None, actor=None) -> dict:
    payload = payload or {}
    reasons = []
    allowed = True

    if action == "create_job":
        job_type = payload.get("job_type")
        if job_type not in ALLOWED_JOB_TYPES:
            allowed = False
            reasons.append(f"Unsupported job type: {job_type}")

        if payload.get("subject_id") is None:
            allowed = False
            reasons.append("subject_id is required.")

    if action == "run_job":
        job_id = payload.get("job_id")
        if job_id is None:
            allowed = False
            reasons.append("job_id is required.")

    if action == "retention_run":
        mode = payload.get("mode", "dry_run")
        if mode == "delete" and not retention_delete_enabled():
            allowed = False
            reasons.append(
                "Delete retention mode requires "
                "SOCMINT_RETENTION_DELETE_ENABLED=1."
            )

    if not reasons:
        reasons.append("Policy gate passed.")

    event_id = db.record_policy_gate_event(
        action=action,
        allowed=allowed,
        reasons=reasons,
        payload=payload,
        actor=actor,
    )

    return {
        "event_id": event_id,
        "action": action,
        "allowed": allowed,
        "reasons": reasons,
    }


def retention_delete_enabled() -> bool:
    value = os.environ.get("SOCMINT_RETENTION_DELETE_ENABLED", "")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def create_workbench_job(
    job_type: str,
    subject_id: int,
    payload: dict | None = None,
    actor=None,
    priority: int = 100,
) -> int:
    payload = payload or {}
    decision = evaluate_policy(
        "create_job",
        {"job_type": job_type, "subject_id": subject_id, "payload": payload},
        actor=actor,
    )
    if not decision["allowed"]:
        raise ValueError("; ".join(decision["reasons"]))

    return db.create_workbench_job(
        subject_id=subject_id,
        job_type=job_type,
        status="queued",
        priority=priority,
        payload=payload,
        actor=actor,
    )


def run_workbench_job(job_id: int, actor=None) -> dict:
    decision = evaluate_policy("run_job", {"job_id": job_id}, actor=actor)
    if not decision["allowed"]:
        raise ValueError("; ".join(decision["reasons"]))

    job = db.get_workbench_job(job_id)
    if not job:
        raise ValueError("Workbench job not found.")

    db.update_workbench_job(
        job_id,
        status="running",
        started_at=datetime.now(UTC),
    )

    try:
        result = dispatch_job(job)
        db.update_workbench_job(
            job_id,
            status="completed",
            result=result,
            finished_at=datetime.now(UTC),
        )
        return result
    except Exception as exc:
        db.update_workbench_job(
            job_id,
            status="failed",
            error=str(exc),
            finished_at=datetime.now(UTC),
        )
        raise


def dispatch_job(job) -> dict:
    payload = _json_loads(job.payload_json)
    subject_id = job.subject_id

    if job.job_type == "spine_run":
        from .spine import run_spine_for_subject

        return run_spine_for_subject(
            subject_id,
            payload.get("connectors") or None,
        )

    if job.job_type == "media_profile_enrichment":
        from .enrichment import enrich_subject_media_profiles

        return enrich_subject_media_profiles(subject_id)

    if job.job_type == "contradiction_detection":
        from .contradictions import detect_subject_contradictions

        return detect_subject_contradictions(subject_id)

    if job.job_type == "dossier_export":
        from .dossier_export import export_dossier

        return export_dossier(
            subject_id,
            formats=payload.get("formats") or ["json", "html", "pdf"],
        )

    if job.job_type == "full_dossier_pipeline":
        return run_full_dossier_pipeline(subject_id, payload)

    raise ValueError(f"Unsupported job type: {job.job_type}")


def run_full_dossier_pipeline(subject_id: int, payload: dict) -> dict:
    from .contradictions import detect_subject_contradictions
    from .dossier_export import export_dossier
    from .enrichment import enrich_subject_media_profiles
    from .identity_graph import build_identity_graph
    from .spine import run_spine_for_subject

    connectors = payload.get("connectors") or None
    formats = payload.get("formats") or ["json", "html", "pdf"]

    spine_result = run_spine_for_subject(subject_id, connectors)
    enrichment_result = enrich_subject_media_profiles(subject_id)
    graph_id = build_identity_graph(subject_id)
    contradiction_result = detect_subject_contradictions(subject_id)
    export_result = export_dossier(subject_id, formats=formats)

    return {
        "subject_id": subject_id,
        "spine": spine_result,
        "media_profile_enrichment": enrichment_result,
        "identity_graph_id": graph_id,
        "contradictions": contradiction_result,
        "export": export_result,
    }


def run_next_workbench_job(actor=None) -> dict | None:
    job = db.get_next_queued_workbench_job()
    if not job:
        return None
    return run_workbench_job(job.id, actor=actor)


def workbench_status() -> dict:
    jobs = db.list_workbench_jobs(limit=1000)
    counts = {}
    for job in jobs:
        counts[job.status] = counts.get(job.status, 0) + 1

    return {
        "jobs_total": len(jobs),
        "by_status": counts,
        "allowed_job_types": sorted(ALLOWED_JOB_TYPES),
    }


def run_retention(mode="dry_run", actor=None) -> dict:
    decision = evaluate_policy(
        "retention_run",
        {"mode": mode},
        actor=actor,
    )
    if not decision["allowed"]:
        raise ValueError("; ".join(decision["reasons"]))

    days = int(os.environ.get("SOCMINT_RETENTION_DAYS", DEFAULT_RETENTION_DAYS))
    result = {
        "mode": mode,
        "retention_days": days,
        "delete_enabled": retention_delete_enabled(),
        "scanned": {
            "workbench_jobs": len(db.list_workbench_jobs(limit=10000)),
            "policy_events": len(db.list_policy_gate_events(limit=10000)),
        },
        "deleted": {},
        "note": "v7.0 retention is audit-first; destructive deletion is gated.",
    }

    run_id = db.create_retention_run(
        mode=mode,
        status="completed",
        result=result,
        actor=actor,
    )
    result["retention_run_id"] = run_id
    return result


def list_workbench_jobs_payload(limit=100):
    jobs = db.list_workbench_jobs(limit=limit)
    return {
        "jobs": [
            {
                "id": job.id,
                "subject_id": job.subject_id,
                "job_type": job.job_type,
                "status": job.status,
                "priority": job.priority,
                "attempts": job.attempts,
                "payload": _json_loads(job.payload_json),
                "result": _json_loads(job.result_json),
                "error": job.error,
                "created_at": job.created_at.isoformat()
                if job.created_at
                else None,
                "updated_at": job.updated_at.isoformat()
                if job.updated_at
                else None,
            }
            for job in jobs
        ]
    }


def policy_events_payload(limit=100):
    events = db.list_policy_gate_events(limit=limit)
    return {
        "events": [
            {
                "id": event.id,
                "action": event.action,
                "allowed": bool(event.allowed),
                "reasons": _json_loads(event.reasons_json, []),
                "payload": _json_loads(event.payload_json),
                "actor": event.actor,
                "created_at": event.created_at.isoformat()
                if event.created_at
                else None,
            }
            for event in events
        ]
    }
