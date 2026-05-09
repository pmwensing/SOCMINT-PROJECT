from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import inspect, text

from . import database as db

REVIEW_STATUSES = {"needs_review", "approved", "rejected", "uncertain"}


@dataclass
class ReviewItem:
    id: str
    subject_id: int | None
    source_table: str
    source_id: int | str | None
    label: str
    value: str
    source: str
    confidence: float | None
    quality: str
    status: str
    created_at: str | None


@dataclass
class ReportRun:
    id: str
    subject_id: int | None
    manifest_path: str
    title: str
    status: str
    created_at: str | None
    file_count: int
    files: list[str]


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def table_exists(table: str) -> bool:
    try:
        db.ensure_configured()
        return table in inspect(db.engine).get_table_names()
    except Exception:
        return False


def columns(table: str) -> set[str]:
    try:
        db.ensure_configured()
        return {c["name"] for c in inspect(db.engine).get_columns(table)}
    except Exception:
        return set()


def safe_rows(sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    try:
        db.ensure_configured()
        with db.engine.connect() as conn:
            result = conn.execute(text(sql), params or {})
            return [dict(row._mapping) for row in result]
    except Exception:
        return []


def quality_from_confidence(confidence: float | None) -> str:
    if confidence is None:
        return "unknown"
    if confidence >= 0.85:
        return "high"
    if confidence >= 0.60:
        return "medium"
    if confidence >= 0.35:
        return "low"
    return "weak"


def row_value(row: dict[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if name in row and row[name] not in (None, ""):
            return row[name]
    return default


def list_enrichment_review_items(
    subject_id: int | None = None,
    status: str | None = None,
    limit: int = 200,
) -> list[ReviewItem]:
    items: list[ReviewItem] = []

    for table in ("spine_observations", "findings"):
        if not table_exists(table):
            continue

        cols = columns(table)
        where = []
        params: dict[str, Any] = {"limit": limit}

        if subject_id is not None and "subject_id" in cols:
            where.append("subject_id = :subject_id")
            params["subject_id"] = subject_id

        where_sql = "WHERE " + " AND ".join(where) if where else ""
        rows = safe_rows(
            f"""
            SELECT *
            FROM {table}
            {where_sql}
            ORDER BY id DESC
            LIMIT :limit
            """,
            params,
        )

        for row in rows:
            confidence_raw = row_value(row, "confidence", "score", default=None)
            try:
                confidence = (
                    float(confidence_raw) if confidence_raw is not None else None
                )
            except (TypeError, ValueError):
                confidence = None

            review_status = row_value(
                row,
                "review_status",
                "analyst_status",
                default="needs_review",
            )

            if status and review_status != status:
                continue

            if table == "spine_observations":
                label = row_value(
                    row,
                    "kind",
                    "observation_type",
                    "type",
                    "label",
                    default="observation",
                )
                value = row_value(
                    row,
                    "value",
                    "content",
                    "raw_value",
                    "summary",
                    default="",
                )
            else:
                label = row_value(
                    row,
                    "finding_type",
                    "kind",
                    "type",
                    "label",
                    default="finding",
                )
                value = row_value(
                    row,
                    "value",
                    "content",
                    "summary",
                    default="",
                )

            items.append(
                ReviewItem(
                    id=f"{table}:{row.get('id')}",
                    subject_id=row_value(row, "subject_id", default=subject_id),
                    source_table=table,
                    source_id=row.get("id"),
                    label=str(label),
                    value=str(value),
                    source=str(
                        row_value(
                            row,
                            "source",
                            "connector",
                            default="unknown",
                        )
                    ),
                    confidence=confidence,
                    quality=quality_from_confidence(confidence),
                    status=str(review_status),
                    created_at=str(row_value(row, "created_at", default="")),
                )
            )

    return items[:limit]


def write_sidecar_review(
    item_id: str,
    status: str,
    note: str | None = None,
) -> dict[str, Any]:
    out_dir = Path("var/socmint/reviews")
    out_dir.mkdir(parents=True, exist_ok=True)

    safe_name = item_id.replace(":", "_").replace("/", "_")
    path = out_dir / f"{safe_name}.json"

    payload = {
        "schema": "socmint.review_decision.v7_2",
        "item_id": item_id,
        "status": status,
        "note": note,
        "updated_at": utc_now(),
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))

    return {
        "updated": True,
        "sidecar": True,
        "path": str(path),
        "item_id": item_id,
        "status": status,
        "note": note,
    }


def set_review_status(
    item_id: str,
    status: str,
    note: str | None = None,
) -> dict[str, Any]:
    if status not in REVIEW_STATUSES:
        raise ValueError(f"Invalid review status: {status}")

    if ":" not in item_id:
        raise ValueError("item_id must be formatted as table:id")

    table, raw_id = item_id.split(":", 1)

    if table not in {"spine_observations", "findings"}:
        raise ValueError(f"Unsupported review table: {table}")

    if not table_exists(table):
        return write_sidecar_review(item_id, status, note)

    cols = columns(table)
    if "review_status" not in cols and "analyst_status" not in cols:
        return write_sidecar_review(item_id, status, note)

    status_col = "review_status" if "review_status" in cols else "analyst_status"
    note_col = None
    for candidate in ("review_note", "analyst_note", "notes"):
        if candidate in cols:
            note_col = candidate
            break

    assignments = [f"{status_col} = :status"]
    params: dict[str, Any] = {"status": status, "id": raw_id}

    if note_col and note is not None:
        assignments.append(f"{note_col} = :note")
        params["note"] = note

    try:
        db.ensure_configured()
        with db.engine.begin() as conn:
            conn.execute(
                text(
                    f"""
                    UPDATE {table}
                    SET {", ".join(assignments)}
                    WHERE id = :id
                    """
                ),
                params,
            )
    except Exception as exc:
        return {
            "updated": False,
            "reason": str(exc),
            "item_id": item_id,
            "status": status,
        }

    return {
        "updated": True,
        "item_id": item_id,
        "status": status,
        "note": note,
    }


def list_report_runs(
    subject_id: int | None = None,
    limit: int = 100,
) -> list[ReportRun]:
    runs: list[ReportRun] = []

    export_root = Path("var/socmint/exports")
    if export_root.exists():
        manifests = sorted(
            export_root.glob("*FULL-REPORT-MANIFEST.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        for path in manifests[:limit]:
            try:
                payload = json.loads(path.read_text(errors="replace"))
            except json.JSONDecodeError:
                payload = {}

            sid = payload.get("subject_id")
            if subject_id is not None and sid != subject_id:
                continue

            files = payload.get("files") or []
            runs.append(
                ReportRun(
                    id=path.stem,
                    subject_id=sid,
                    manifest_path=str(path),
                    title=path.name,
                    status="complete",
                    created_at=payload.get("generated_at"),
                    file_count=len(files),
                    files=[str(f) for f in files],
                )
            )

    if table_exists("dossier_exports"):
        cols = columns("dossier_exports")
        where = []
        params: dict[str, Any] = {"limit": limit}

        if subject_id is not None and "subject_id" in cols:
            where.append("subject_id = :subject_id")
            params["subject_id"] = subject_id

        where_sql = "WHERE " + " AND ".join(where) if where else ""
        rows = safe_rows(
            f"""
            SELECT *
            FROM dossier_exports
            {where_sql}
            ORDER BY id DESC
            LIMIT :limit
            """,
            params,
        )

        for row in rows:
            sid = row_value(row, "subject_id", default=subject_id)
            manifest = str(row_value(row, "path", "file_path", default=""))

            runs.append(
                ReportRun(
                    id=f"dossier_exports:{row.get('id')}",
                    subject_id=sid,
                    manifest_path=manifest,
                    title=str(
                        row_value(
                            row,
                            "title",
                            "report_type",
                            default=f"Dossier export {row.get('id')}",
                        )
                    ),
                    status=str(row_value(row, "status", default="complete")),
                    created_at=str(row_value(row, "created_at", default="")),
                    file_count=1 if manifest else 0,
                    files=[manifest] if manifest else [],
                )
            )

    return runs[:limit]


def review_summary() -> dict[str, Any]:
    items = list_enrichment_review_items(limit=500)
    reports = list_report_runs(limit=100)

    status_counts: dict[str, int] = {}
    quality_counts: dict[str, int] = {}

    for item in items:
        status_counts[item.status] = status_counts.get(item.status, 0) + 1
        quality_counts[item.quality] = quality_counts.get(item.quality, 0) + 1

    return {
        "schema": "socmint.report_review.summary.v7_2",
        "generated_at": utc_now(),
        "review_item_count": len(items),
        "report_run_count": len(reports),
        "status_counts": status_counts,
        "quality_counts": quality_counts,
    }


def review_items_payload(
    subject_id: int | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    return {
        "schema": "socmint.report_review.items.v7_2",
        "generated_at": utc_now(),
        "items": [
            asdict(item)
            for item in list_enrichment_review_items(
                subject_id=subject_id,
                status=status,
            )
        ],
    }


def report_runs_payload(subject_id: int | None = None) -> dict[str, Any]:
    return {
        "schema": "socmint.report_review.runs.v7_2",
        "generated_at": utc_now(),
        "reports": [asdict(run) for run in list_report_runs(subject_id=subject_id)],
    }
