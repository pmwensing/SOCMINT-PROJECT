import logging
import re
from collections import Counter
from datetime import UTC, datetime, timedelta

from . import database as db

logger = logging.getLogger(__name__)
STALE_RUNNING_AFTER = timedelta(minutes=30)
SPINE_REQUESTED_BY = re.compile(r"^spine:(?P<subject_id>\d+):")


def build_dossier(target, target_type, enabled_tools=None):
    from .main import build_dossier as main_build_dossier
    return main_build_dossier(target, target_type, enabled_tools=enabled_tools)


def enrich_dossier(dossier):
    from .enrichment import enrich_dossier as run_enrichment
    return run_enrichment(dossier)


def _spine_subject_id(job: dict) -> int | None:
    raw = str(job.get("requested_by") or "")
    match = SPINE_REQUESTED_BY.match(raw)
    return int(match.group("subject_id")) if match else None


def _process_spine_job(job: dict, subject_id: int) -> dict:
    from .spine import HIGH_VALUE_CONNECTORS, correlate_subject, run_connector_for_seed

    seed = None
    for candidate in db.list_spine_seeds(subject_id):
        if candidate.seed_type == job["target_type"] and candidate.normalized_value == job["target_value"]:
            seed = candidate
            break
    if seed is None:
        raise ValueError(f"No matching spine seed for subject {subject_id}: {job['target_type']} {job['target_value']}")

    run_ids = []
    skipped = []
    for raw_key in job["tools"]:
        key = str(raw_key).strip()
        spec = HIGH_VALUE_CONNECTORS.get(key)
        if not spec:
            skipped.append({"connector": key, "reason": "not in HIGH_VALUE_CONNECTORS"})
            continue
        if seed.seed_type not in spec["seed_types"]:
            skipped.append({"connector": key, "reason": f"seed type {seed.seed_type} not supported", "supported": spec["seed_types"]})
            continue
        run_ids.append(run_connector_for_seed(subject_id, seed, key, spec))

    if not run_ids:
        raise ValueError(f"Spine job created no connector runs; tools={job['tools']} seed_type={seed.seed_type} skipped={skipped}")

    correlate_subject(subject_id)
    db.finish_scan_job(job["id"], "completed", target_id=None)
    logger.info("Completed spine scan job %s for subject %s", job["id"], subject_id)
    return {"id": job["id"], "status": "completed", "subject_id": subject_id, "run_ids": run_ids, "spine": True}


def process_next_scan_job():
    job = db.claim_next_scan_job()
    if not job:
        return None

    try:
        subject_id = _spine_subject_id(job)
        if subject_id is not None:
            return _process_spine_job(job, subject_id)

        dossier = build_dossier(job["target_value"], job["target_type"], enabled_tools=set(job["tools"]))
        if job["enrich"]:
            dossier = enrich_dossier(dossier)
        target_id = db.save_dossier(dossier)
        db.finish_scan_job(job["id"], "completed", target_id=target_id)
        logger.info("Completed scan job %s", job["id"])
        return {"id": job["id"], "status": "completed", "target_id": target_id}
    except Exception as exc:
        logger.exception("Scan job %s failed", job["id"])
        db.finish_scan_job(job["id"], "failed", error=str(exc))
        return {"id": job["id"], "status": "failed", "error": str(exc)}


def process_scan_jobs(max_jobs=1):
    processed = []
    for _ in range(max_jobs):
        result = process_next_scan_job()
        if not result:
            break
        processed.append(result)
    return processed


def scan_job_health(limit=250):
    jobs = db.list_scan_jobs(limit=limit)
    now = datetime.now(UTC)
    counts = Counter(job.status for job in jobs)
    stale = []
    for job in jobs:
        if job.status != "running" or not job.started_at:
            continue
        started_at = job.started_at
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=UTC)
        age_seconds = int((now - started_at).total_seconds())
        if age_seconds >= int(STALE_RUNNING_AFTER.total_seconds()):
            stale.append({"id": job.id, "target_value": job.target_value, "started_at": job.started_at.isoformat(), "age_seconds": age_seconds})
    return {
        "schema": "socmint.scan_job_health.v7_8_1",
        "generated_at": now.isoformat(),
        "counts": dict(counts),
        "queue_depth": counts.get("queued", 0),
        "running": counts.get("running", 0),
        "failed": counts.get("failed", 0),
        "stale_running_after_seconds": int(STALE_RUNNING_AFTER.total_seconds()),
        "stale_running_jobs": stale,
        "needs_attention": bool(stale or counts.get("failed", 0)),
    }


def requeue_scan_job(job_id):
    job = db.update_scan_job_status(job_id, "queued", error=None)
    if not job:
        raise ValueError("Scan job not found.")
    return {"id": job.id, "status": job.status}


def cancel_scan_job(job_id, reason="Canceled by operator."):
    job = db.update_scan_job_status(job_id, "canceled", error=reason)
    if not job:
        raise ValueError("Scan job not found.")
    return {"id": job.id, "status": job.status, "reason": reason}
