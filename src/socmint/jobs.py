import logging

from . import database as db
from .enrichment import enrich_dossier
from .main import build_dossier

logger = logging.getLogger(__name__)


def process_next_scan_job():
    job = db.claim_next_scan_job()
    if not job:
        return None

    try:
        dossier = build_dossier(
            job["target_value"],
            job["target_type"],
            enabled_tools=set(job["tools"]),
        )
        if job["enrich"]:
            dossier = enrich_dossier(dossier)
        target_id = db.save_dossier(dossier)
        db.finish_scan_job(job["id"], "completed", target_id=target_id)
        logger.info("Completed scan job %s", job["id"])
        return {"id": job["id"], "status": "completed"}
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
