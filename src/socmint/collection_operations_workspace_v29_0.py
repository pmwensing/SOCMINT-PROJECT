from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import inspect, text

from . import database

SCHEMA = "socmint.collection_operations_workspace.v29_0"
VERSION = "v29.0.0"


def _iso(value: Any) -> str | None:
    return value.isoformat() if value else None


def _json(value: Any) -> Any:
    if value in (None, ""):
        return None
    if isinstance(value, (dict, list, int, float, bool)):
        return value
    try:
        return json.loads(str(value))
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def _age_hours(value: Any, now: datetime) -> float | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return max(0.0, (now - value).total_seconds() / 3600.0)


def _scan_jobs(limit: int = 1000) -> list[dict[str, Any]]:
    database.ensure_configured()
    session = database.Session()
    try:
        rows = session.query(database.ScanJob).order_by(database.ScanJob.created_at.desc()).limit(limit).all()
        return [{
            "job_id": row.id,
            "target_id": row.target_id,
            "target_value": row.target_value,
            "target_type": row.target_type,
            "tools": _json(row.tools) or row.tools,
            "enrich": bool(row.enrich),
            "status": str(row.status or "unknown").lower(),
            "requested_by": row.requested_by,
            "error_present": bool(row.error),
            "created_at": _iso(row.created_at),
            "started_at": _iso(row.started_at),
            "finished_at": _iso(row.finished_at),
            "_created_at": row.created_at,
            "_started_at": row.started_at,
            "_finished_at": row.finished_at,
        } for row in rows]
    finally:
        session.close()


def _connector_runs(limit: int = 2000) -> list[dict[str, Any]]:
    database.ensure_configured()
    session = database.Session()
    try:
        rows = session.query(database.ConnectorRun).order_by(database.ConnectorRun.created_at.desc()).limit(limit).all()
        return [{
            "run_id": row.id,
            "target_id": row.target_id,
            "target_value": row.target_value,
            "target_type": row.target_type,
            "connector": row.connector,
            "status": str(row.status or "unknown").lower(),
            "raw_result_present": bool(row.raw_result),
            "raw_result_size": len(row.raw_result or ""),
            "error_present": bool(row.error),
            "created_at": _iso(row.created_at),
            "_created_at": row.created_at,
        } for row in rows]
    finally:
        session.close()


def _findings(limit: int = 5000) -> list[dict[str, Any]]:
    database.ensure_configured()
    session = database.Session()
    try:
        rows = session.query(database.Finding).order_by(database.Finding.created_at.desc()).limit(limit).all()
        return [{
            "finding_id": row.id,
            "connector_run_id": row.connector_run_id,
            "target_id": row.target_id,
            "source": row.source,
            "type": row.type,
            "confidence": row.confidence,
            "context_present": bool(row.context),
            "created_at": _iso(row.created_at),
        } for row in rows]
    finally:
        session.close()


def _results(limit: int = 5000) -> list[dict[str, Any]]:
    database.ensure_configured()
    session = database.Session()
    try:
        rows = session.query(database.Result).order_by(database.Result.timestamp.desc()).limit(limit).all()
        return [{
            "result_id": row.id,
            "target_id": row.target_id,
            "tool_id": row.tool_id,
            "data_present": bool(row.data),
            "data_size": len(row.data or ""),
            "timestamp": _iso(row.timestamp),
        } for row in rows]
    finally:
        session.close()


def _media(limit: int = 5000) -> list[dict[str, Any]]:
    database.ensure_configured()
    session = database.Session()
    try:
        rows = session.query(database.Media).order_by(database.Media.created_at.desc()).limit(limit).all()
        return [{
            "media_id": row.id,
            "target_id": row.target_id,
            "profile_id": row.profile_id,
            "source_present": bool(row.source_url),
            "path_present": bool(row.path),
            "checksum_present": bool(row.checksum),
            "content_type": row.content_type,
            "created_at": _iso(row.created_at),
        } for row in rows]
    finally:
        session.close()


def _optional_table_summary() -> dict[str, Any]:
    database.ensure_configured()
    engine = database.engine
    inspector = inspect(engine)
    available = set(inspector.get_table_names())
    requested = (
        "spine_subjects",
        "spine_seeds",
        "spine_connector_runs",
        "spine_observations",
        "spine_dossier_assertions",
    )
    summaries: dict[str, Any] = {}
    with engine.connect() as connection:
        for table_name in requested:
            if table_name not in available:
                summaries[table_name] = {"available": False, "record_count": 0}
                continue
            columns = [column["name"] for column in inspector.get_columns(table_name)]
            count = int(connection.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar() or 0)
            summaries[table_name] = {"available": True, "record_count": count, "columns": columns}
    return summaries


def build_collection_operations_workspace(*, stale_after_hours: int = 24) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    threshold = max(1, int(stale_after_hours))
    jobs = _scan_jobs()
    runs = _connector_runs()
    findings = _findings()
    results = _results()
    media = _media()
    optional = _optional_table_summary()

    run_findings: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for item in findings:
        run_findings[int(item["connector_run_id"])].append(item)

    target_results = Counter(item["target_id"] for item in results)
    target_media = Counter(item["target_id"] for item in media)
    target_runs = Counter(item["target_id"] for item in runs if item["target_id"] is not None)

    stale_jobs = []
    retry_eligibility = []
    for job in jobs:
        age = _age_hours(job.get("_started_at") or job.get("_created_at"), now)
        active = job["status"] in {"queued", "pending", "running", "in_progress"}
        stale = bool(active and age is not None and age >= threshold)
        if stale:
            stale_jobs.append({key: value for key, value in job.items() if not key.startswith("_")})
        retryable = job["status"] in {"failed", "error", "blocked"} and bool(job["target_value"] and job["tools"])
        retry_eligibility.append({
            "job_id": job["job_id"],
            "eligible": retryable,
            "reason": "failed_with_reconstructable_input" if retryable else "not_retryable_from_current_state",
            "retry_execution_available": False,
        })

    duplicate_run_groups = []
    grouped_runs: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for run in runs:
        grouped_runs[(str(run["connector"]), str(run["target_type"]), str(run["target_value"]))].append(run)
    for key, items in grouped_runs.items():
        if len(items) > 1:
            duplicate_run_groups.append({
                "connector": key[0],
                "target_type": key[1],
                "target_value": key[2],
                "run_count": len(items),
                "run_ids": [item["run_id"] for item in items],
            })

    collection_inventory = []
    for run in runs:
        linked_findings = run_findings.get(int(run["run_id"]), [])
        provenance_complete = bool(run["connector"] and run["target_value"] and run["target_type"] and run["created_at"])
        output_count = len(linked_findings)
        collection_inventory.append({
            **{key: value for key, value in run.items() if not key.startswith("_")},
            "finding_output_count": output_count,
            "finding_types": sorted({item["type"] for item in linked_findings}),
            "provenance_complete": provenance_complete,
            "dossier_value": "contributing" if output_count else "unproven",
            "human_review_required": bool(output_count or run["error_present"]),
        })

    provenance_findings = [
        {"severity": "high", "key": "incomplete_connector_run_provenance", "run_id": item["run_id"]}
        for item in collection_inventory if not item["provenance_complete"]
    ]
    scope_findings = [
        {"severity": "medium", "key": "collection_without_requesting_actor", "job_id": item["job_id"]}
        for item in jobs if not item["requested_by"]
    ]
    failure_findings = [
        {"severity": "high", "key": "collection_job_failed", "job_id": item["job_id"]}
        for item in jobs if item["status"] in {"failed", "error", "blocked"} or item["error_present"]
    ]
    findings_all = [
        *failure_findings,
        *[{"severity": "high", "key": "collection_job_stale", "job_id": item["job_id"]} for item in stale_jobs],
        *[{"severity": "low", "key": "duplicate_collection_runs", **item} for item in duplicate_run_groups],
        *provenance_findings,
        *scope_findings,
    ]

    target_bindings = []
    target_ids = sorted({item for item in [*target_runs.keys(), *target_results.keys(), *target_media.keys()] if item is not None})
    for target_id in target_ids:
        target_bindings.append({
            "target_id": target_id,
            "connector_run_count": target_runs[target_id],
            "result_count": target_results[target_id],
            "media_count": target_media[target_id],
            "case_binding_available": False,
            "entity_binding_available": True,
        })

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "ready",
        "collection_inventory": collection_inventory,
        "collection_run_count": len(runs),
        "job_inventory": [{key: value for key, value in item.items() if not key.startswith("_")} for item in jobs],
        "job_count": len(jobs),
        "job_status_counts": dict(sorted(Counter(item["status"] for item in jobs).items())),
        "connector_status_counts": dict(sorted(Counter(item["status"] for item in runs).items())),
        "stale_jobs": stale_jobs,
        "stale_job_count": len(stale_jobs),
        "duplicate_run_groups": duplicate_run_groups,
        "duplicate_run_group_count": len(duplicate_run_groups),
        "retry_eligibility": retry_eligibility,
        "retry_eligible_count": sum(item["eligible"] for item in retry_eligibility),
        "evidence_summary": {
            "result_count": len(results),
            "media_count": len(media),
            "finding_count": len(findings),
            "finding_type_counts": dict(sorted(Counter(item["type"] for item in findings).items())),
        },
        "observation_summary": {
            "finding_count": len(findings),
            "spine_observation_count": optional.get("spine_observations", {}).get("record_count", 0),
        },
        "provenance_summary": {
            "complete_connector_run_count": sum(item["provenance_complete"] for item in collection_inventory),
            "incomplete_connector_run_count": sum(not item["provenance_complete"] for item in collection_inventory),
            "media_checksum_complete_count": sum(item["checksum_present"] for item in media),
            "media_checksum_incomplete_count": sum(not item["checksum_present"] for item in media),
        },
        "target_bindings": target_bindings,
        "optional_spine_tables": optional,
        "dossier_value_summary": {
            "contributing_run_count": sum(item["dossier_value"] == "contributing" for item in collection_inventory),
            "unproven_run_count": sum(item["dossier_value"] == "unproven" for item in collection_inventory),
            "spine_assertion_count": optional.get("spine_dossier_assertions", {}).get("record_count", 0),
        },
        "operator_findings": findings_all,
        "operator_finding_count": len(findings_all),
        "stale_after_hours": threshold,
        "read_only": True,
        "connector_execution_available": False,
        "job_mutation_available": False,
        "retry_execution_available": False,
        "credential_rotation_available": False,
        "secret_values_visible": False,
        "case_access_scope_changed": False,
        "evidence_rewritten": False,
        "next_action": "review_collection_operations_findings",
    }
