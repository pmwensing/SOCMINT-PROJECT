from __future__ import annotations

import hashlib
import html
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import inspect, text

from . import database as db
from .config import load_settings

DOSSIER_SCHEMA = "socmint.full_entity_profile_dossier.v7_8_1"
EXPORT_SCHEMA = "socmint.full_entity_profile_dossier_export.v7_5_1"
MANIFEST_SCHEMA = "socmint.full_entity_profile_dossier_manifest.v7_5_1"
DIAGNOSTIC_OBSERVATION_TYPES = {"connector_no_result", "seed_expansion_candidate"}
DIAGNOSTIC_ARCHIVE_TYPES = {"archive_candidate"}


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def dossier_root() -> Path:
    settings = load_settings(require_secret=False)
    root = Path(settings.data_dir) / "dossiers"
    root.mkdir(parents=True, exist_ok=True)
    return root


def safe_dossier_path(name: str) -> Path:
    root = dossier_root().resolve()
    path = (root / Path(name).name).resolve()
    if root not in path.parents and path != root:
        raise ValueError("Dossier path escapes dossier root")
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(str(path))
    return path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b=""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest_entry(path: Path, role: str) -> dict[str, Any]:
    return {
        "role": role,
        "name": path.name,
        "path": str(path),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def _table_names() -> set[str]:
    try:
        return set(inspect(db.engine).get_table_names())
    except Exception:
        return set()


def _columns_for(table: str) -> set[str]:
    try:
        return {col["name"] for col in inspect(db.engine).get_columns(table)}
    except Exception:
        return set()


def _rows_for_subject(table: str, subject_id: int, limit: int = 200) -> list[dict[str, Any]]:
    if table not in _table_names():
        return []
    columns = _columns_for(table)
    keys = ["subject_id", "spine_subject_id", "entity_id", "target_id", "id"]
    where_key = next((key for key in keys if key in columns), None)
    if where_key is None:
        return []
    with db.engine.connect() as conn:
        result = conn.execute(
            text(f"SELECT * FROM {table} WHERE {where_key} = :subject_id LIMIT :limit"),
            {"subject_id": subject_id, "limit": limit},
        )
        return [dict(row._mapping) for row in result]


def _json_safe(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _safe_rows(table: str, subject_id: int, limit: int = 200) -> list[dict[str, Any]]:
    rows = _rows_for_subject(table, subject_id, limit=limit)
    return [{key: _json_safe(value) for key, value in row.items()} for row in rows]


def _score_for_rows(rows: list[dict[str, Any]]) -> float:
    if not rows:
        return 0.0
    values: list[float] = []
    for row in rows:
        for key in ("confidence", "score", "risk_score"):
            value = row.get(key)
            if value is None:
                continue
            try:
                values.append(float(value))
            except (TypeError, ValueError):
                continue
    if not values:
        return 0.5
    return round(sum(values) / len(values), 3)


def _evidence_rows(subject_id: int) -> list[dict[str, Any]]:
    rows = []
    for table in ("evidence", "evidence_items", "evidence_intake"):
        rows.extend(_safe_rows(table, subject_id, limit=500))
    return rows


def _finding_rows(subject_id: int) -> list[dict[str, Any]]:
    rows = []
    for table in ("findings", "normalized_findings", "identity_findings"):
        rows.extend(_safe_rows(table, subject_id, limit=500))
    return rows


def _timeline_rows(subject_id: int) -> list[dict[str, Any]]:
    rows = []
    for table in ("events", "timeline_events", "case_events"):
        rows.extend(_safe_rows(table, subject_id, limit=500))
    return rows


def _claim_rows(subject_id: int) -> list[dict[str, Any]]:
    rows = []
    for table in ("claims", "assertions", "subject_claims"):
        rows.extend(_safe_rows(table, subject_id, limit=500))
    return rows


def _risk_rows(subject_id: int) -> list[dict[str, Any]]:
    rows = []
    for table in ("risk_scores", "subject_risks", "threat_scores"):
        rows.extend(_safe_rows(table, subject_id, limit=200))
    return rows


def _identity_rows(subject_id: int) -> list[dict[str, Any]]:
    rows = []
    for table in ("identities", "identity_clusters", "entity_resolution_links"):
        rows.extend(_safe_rows(table, subject_id, limit=500))
    return rows


def _narrative(sections: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    total_items = sum(len(items) for items in sections.values())
    strongest = sorted(
        (
            {"section": section, "score": _score_for_rows(rows), "count": len(rows)}
            for section, rows in sections.items()
        ),
        key=lambda item: (item["score"], item["count"]),
        reverse=True,
    )
    return {
        "summary": (
            "No subject evidence has been collected yet."
            if total_items == 0
            else f"Compiled {total_items} subject-linked records across dossier sections."
        ),
        "strongest_sections": strongest[:3],
    }
