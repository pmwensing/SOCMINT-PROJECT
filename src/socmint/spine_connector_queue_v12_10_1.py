from __future__ import annotations

from typing import Any

from . import database as db
from .connectors import connector_mode_report
from .spine import HIGH_VALUE_CONNECTORS


def spine_requested_by(subject_id: int, actor: str | None = None) -> str:
    safe_actor = (actor or "spine-ui").replace(":", "_")
    return f"spine:{subject_id}:{safe_actor}"


def queue_subject_connector_jobs(
    subject_id: int, connectors: list[str] | None = None, actor: str | None = None
) -> dict[str, Any]:
    subject = db.get_spine_subject(subject_id)
    if not subject:
        raise ValueError("Subject not found.")

    selected = connectors or list(HIGH_VALUE_CONNECTORS)
    job_ids: list[int] = []
    seed_rows: list[dict[str, Any]] = []

    for seed in db.list_spine_seeds(subject_id):
        compatible = [
            key
            for key in selected
            if key in HIGH_VALUE_CONNECTORS
            and seed.seed_type in HIGH_VALUE_CONNECTORS[key]["seed_types"]
        ]
        if not compatible:
            continue
        job = db.create_scan_job(
            target_value=seed.normalized_value,
            target_type=seed.seed_type,
            tools=compatible,
            enrich=False,
            requested_by=spine_requested_by(subject_id, actor),
        )
        job_ids.append(job.id)
        seed_rows.append(
            {
                "seed_id": seed.id,
                "seed_type": seed.seed_type,
                "job_id": job.id,
                "connectors": compatible,
            }
        )

    return {
        "schema": "socmint.spine_connector_queue.v12_10_1",
        "subject_id": subject_id,
        "queued_job_ids": job_ids,
        "queued_count": len(job_ids),
        "seeds": seed_rows,
        "mode": connector_mode_report(),
        "note": "Connector jobs queued for worker processing; web request does not run live connector subprocesses.",
    }
