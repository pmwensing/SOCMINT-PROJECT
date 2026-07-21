from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text

from . import database as db
from .evidence_findings import ensure_findings_schema

ANALYSIS_SCHEMA = "socmint.evidence_analysis.v39_2_0"
_ALLOWED_RELATIONSHIPS = {"supports", "contradicts", "qualifies", "duplicates", "context"}
_SOURCE_QUALITY = {
    "official_record": 1.00,
    "original_email": 0.95,
    "original_photo": 0.90,
    "original_video": 0.90,
    "contemporaneous_note": 0.80,
    "witness_statement": 0.75,
    "secondary_report": 0.60,
    "working_hypothesis": 0.30,
}


def _now():
    return db.utc_now()


def _json(value: Any) -> str:
    return json.dumps(value if value is not None else {}, sort_keys=True)


def ensure_analysis_schema() -> None:
    ensure_findings_schema()
    session = db.Session()
    try:
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS observation_relationships (
                id INTEGER PRIMARY KEY,
                case_id INTEGER NOT NULL,
                source_observation_id INTEGER NOT NULL,
                target_observation_id INTEGER NOT NULL,
                relationship VARCHAR(64) NOT NULL,
                rationale TEXT,
                metadata_json TEXT NOT NULL,
                actor VARCHAR(255),
                created_at DATETIME NOT NULL,
                UNIQUE(source_observation_id, target_observation_id, relationship)
            )
        """))
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS evidence_source_assessments (
                id INTEGER PRIMARY KEY,
                case_id INTEGER NOT NULL,
                evidence_item_id INTEGER NOT NULL,
                source_class VARCHAR(64) NOT NULL,
                quality_score REAL NOT NULL,
                rationale TEXT,
                metadata_json TEXT NOT NULL,
                actor VARCHAR(255),
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                UNIQUE(evidence_item_id)
            )
        """))
        session.commit()
    finally:
        session.close()


def link_observations(
    source_observation_id: int,
    target_observation_id: int,
    *,
    relationship: str,
    rationale: str | None = None,
    metadata: dict[str, Any] | None = None,
    actor: str | None = None,
) -> dict[str, Any]:
    if relationship not in _ALLOWED_RELATIONSHIPS:
        raise ValueError("invalid observation relationship")
    if int(source_observation_id) == int(target_observation_id):
        raise ValueError("an observation cannot relate to itself")
    ensure_analysis_schema()
    session = db.Session()
    try:
        rows = session.execute(text("""
            SELECT id, case_id FROM evidence_observations
            WHERE id=:source_id OR id=:target_id
        """), {
            "source_id": int(source_observation_id),
            "target_id": int(target_observation_id),
        }).mappings().all()
        if len(rows) != 2:
            raise ValueError("both observations must exist")
        case_ids = {int(row["case_id"]) for row in rows}
        if len(case_ids) != 1:
            raise ValueError("cross-case observation relationships are forbidden")
        case_id = case_ids.pop()
        session.execute(text("""
            INSERT INTO observation_relationships
            (case_id, source_observation_id, target_observation_id, relationship,
             rationale, metadata_json, actor, created_at)
            VALUES
            (:case_id, :source_id, :target_id, :relationship,
             :rationale, :metadata_json, :actor, :now)
            ON CONFLICT(source_observation_id, target_observation_id, relationship)
            DO NOTHING
        """), {
            "case_id": case_id,
            "source_id": int(source_observation_id),
            "target_id": int(target_observation_id),
            "relationship": relationship,
            "rationale": rationale,
            "metadata_json": _json(metadata or {}),
            "actor": actor,
            "now": _now(),
        })
        session.commit()
        row = session.execute(text("""
            SELECT * FROM observation_relationships
            WHERE source_observation_id=:source_id
              AND target_observation_id=:target_id
              AND relationship=:relationship
        """), {
            "source_id": int(source_observation_id),
            "target_id": int(target_observation_id),
            "relationship": relationship,
        }).mappings().one()
    finally:
        session.close()
    db.record_audit_event(
        action="evidence_observations_linked",
        actor=actor,
        details={
            "source_observation_id": int(source_observation_id),
            "target_observation_id": int(target_observation_id),
            "relationship": relationship,
        },
    )
    return {"schema": ANALYSIS_SCHEMA, "relationship": dict(row)}


def assess_source_quality(
    evidence_item_id: int,
    *,
    source_class: str,
    quality_score: float | None = None,
    rationale: str | None = None,
    metadata: dict[str, Any] | None = None,
    actor: str | None = None,
) -> dict[str, Any]:
    if source_class not in _SOURCE_QUALITY:
        raise ValueError("invalid source class")
    score = _SOURCE_QUALITY[source_class] if quality_score is None else float(quality_score)
    if not 0.0 <= score <= 1.0:
        raise ValueError("quality score must be between 0 and 1")
    ensure_analysis_schema()
    session = db.Session()
    try:
        evidence = session.execute(
            text("SELECT id, case_id FROM evidence_items WHERE id=:id"),
            {"id": int(evidence_item_id)},
        ).mappings().first()
        if not evidence:
            raise ValueError("evidence item does not exist")
        now = _now()
        session.execute(text("""
            INSERT INTO evidence_source_assessments
            (case_id, evidence_item_id, source_class, quality_score, rationale,
             metadata_json, actor, created_at, updated_at)
            VALUES
            (:case_id, :evidence_item_id, :source_class, :quality_score, :rationale,
             :metadata_json, :actor, :now, :now)
            ON CONFLICT(evidence_item_id) DO UPDATE SET
                source_class=excluded.source_class,
                quality_score=excluded.quality_score,
                rationale=excluded.rationale,
                metadata_json=excluded.metadata_json,
                actor=excluded.actor,
                updated_at=excluded.updated_at
        """), {
            "case_id": int(evidence["case_id"]),
            "evidence_item_id": int(evidence_item_id),
            "source_class": source_class,
            "quality_score": score,
            "rationale": rationale,
            "metadata_json": _json(metadata or {}),
            "actor": actor,
            "now": now,
        })
        session.commit()
        row = session.execute(
            text("SELECT * FROM evidence_source_assessments WHERE evidence_item_id=:id"),
            {"id": int(evidence_item_id)},
        ).mappings().one()
    finally:
        session.close()
    db.record_audit_event(
        action="evidence_source_quality_assessed",
        actor=actor,
        details={"evidence_item_id": int(evidence_item_id), "source_class": source_class, "quality_score": score},
    )
    return {"schema": ANALYSIS_SCHEMA, "assessment": dict(row)}


def observation_effective_confidence(observation_id: int) -> dict[str, Any]:
    ensure_analysis_schema()
    session = db.Session()
    try:
        row = session.execute(text("""
            SELECT eo.id, eo.case_id, eo.confidence AS analyst_confidence,
                   eo.status, esa.quality_score, esa.source_class
            FROM evidence_observations eo
            LEFT JOIN evidence_source_assessments esa
              ON esa.evidence_item_id = eo.evidence_item_id
            WHERE eo.id=:id
        """), {"id": int(observation_id)}).mappings().first()
        if not row:
            raise ValueError("observation does not exist")
    finally:
        session.close()
    source_quality = float(row["quality_score"]) if row["quality_score"] is not None else 0.50
    analyst_confidence = float(row["analyst_confidence"])
    effective = round(analyst_confidence * source_quality, 4)
    return {
        "schema": ANALYSIS_SCHEMA,
        "observation_id": int(observation_id),
        "analyst_confidence": analyst_confidence,
        "source_quality": source_quality,
        "source_class": row["source_class"] or "unassessed",
        "effective_confidence": effective,
        "review_status": row["status"],
    }


def claim_proof_coverage(case_id: int, claim_key: str) -> dict[str, Any]:
    """Return a conservative claim coverage summary from approved findings only."""
    ensure_analysis_schema()
    session = db.Session()
    try:
        findings = session.execute(text("""
            SELECT ef.id, ef.finding_key, ef.statement, ef.classification, ef.status,
                   ft.relationship
            FROM finding_targets ft
            JOIN evidence_findings ef ON ef.id = ft.finding_id
            WHERE ft.case_id=:case_id
              AND ft.target_type='claim'
              AND ft.target_key=:claim_key
            ORDER BY ef.id
        """), {"case_id": int(case_id), "claim_key": claim_key}).mappings().all()
        approved_ids = [int(row["id"]) for row in findings if row["status"] == "approved"]
        approved_observation_count = 0
        source_count = 0
        if approved_ids:
            placeholders = ",".join(f":id_{index}" for index, _ in enumerate(approved_ids))
            params = {f"id_{index}": value for index, value in enumerate(approved_ids)}
            approved_observation_count = int(session.execute(text(f"""
                SELECT COUNT(DISTINCT eo.id)
                FROM finding_observations fo
                JOIN evidence_observations eo ON eo.id=fo.observation_id
                WHERE fo.finding_id IN ({placeholders})
                  AND eo.status='approved'
            """), params).scalar_one())
            source_count = int(session.execute(text(f"""
                SELECT COUNT(DISTINCT eo.evidence_item_id)
                FROM finding_observations fo
                JOIN evidence_observations eo ON eo.id=fo.observation_id
                WHERE fo.finding_id IN ({placeholders})
                  AND eo.status='approved'
            """), params).scalar_one())
    finally:
        session.close()

    approved_findings = [dict(row) for row in findings if row["status"] == "approved"]
    contradicting = [row for row in approved_findings if row["relationship"] == "contradicts"]
    supporting = [row for row in approved_findings if row["relationship"] == "supports"]
    if not approved_findings:
        state = "unproven"
    elif supporting and contradicting:
        state = "contested"
    elif supporting and source_count >= 2:
        state = "corroborated"
    elif supporting:
        state = "supported"
    else:
        state = "context_only"
    return {
        "schema": ANALYSIS_SCHEMA,
        "case_id": int(case_id),
        "claim_key": claim_key,
        "coverage_state": state,
        "approved_finding_count": len(approved_findings),
        "approved_observation_count": approved_observation_count,
        "distinct_source_count": source_count,
        "supporting_finding_count": len(supporting),
        "contradicting_finding_count": len(contradicting),
        "findings": [dict(row) for row in findings],
    }
