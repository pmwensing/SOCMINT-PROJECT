from __future__ import annotations

import datetime as dt
import hashlib
import json
from typing import Any

from sqlalchemy import text

from . import database as db

EVIDENCE_OS_SCHEMA = "socmint.evidence_os.v39_0_0"


def _now() -> dt.datetime:
    return db.utc_now()


def _json(value: Any) -> str:
    return json.dumps(value if value is not None else {}, sort_keys=True)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def ensure_evidence_os_schema() -> None:
    """Create the first governed Evidence OS tables.

    This intentionally uses additive tables and immutable source rows so the
    feature can ship without rewriting existing dossier or case data.
    """
    db.ensure_configured()
    session = db.Session()
    try:
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS evidence_items (
                id INTEGER PRIMARY KEY,
                case_id INTEGER NOT NULL,
                evidence_key VARCHAR(128) NOT NULL,
                media_type VARCHAR(128) NOT NULL,
                source_name VARCHAR(255) NOT NULL,
                source_locator TEXT,
                captured_at DATETIME,
                imported_at DATETIME NOT NULL,
                sha256 VARCHAR(64) NOT NULL,
                byte_length INTEGER NOT NULL,
                metadata_json TEXT NOT NULL,
                actor VARCHAR(255),
                UNIQUE(case_id, evidence_key),
                UNIQUE(case_id, sha256)
            )
        """))
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS evidence_observations (
                id INTEGER PRIMARY KEY,
                case_id INTEGER NOT NULL,
                evidence_item_id INTEGER NOT NULL,
                observation_key VARCHAR(128) NOT NULL,
                statement TEXT NOT NULL,
                classification VARCHAR(64) NOT NULL,
                confidence REAL NOT NULL,
                status VARCHAR(64) NOT NULL,
                rationale TEXT,
                metadata_json TEXT NOT NULL,
                actor VARCHAR(255),
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                UNIQUE(case_id, observation_key)
            )
        """))
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS evidence_findings (
                id INTEGER PRIMARY KEY,
                case_id INTEGER NOT NULL,
                finding_key VARCHAR(128) NOT NULL,
                statement TEXT NOT NULL,
                classification VARCHAR(64) NOT NULL,
                status VARCHAR(64) NOT NULL,
                rationale TEXT,
                metadata_json TEXT NOT NULL,
                approved_by VARCHAR(255),
                approved_at DATETIME,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                UNIQUE(case_id, finding_key)
            )
        """))
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS finding_observations (
                finding_id INTEGER NOT NULL,
                observation_id INTEGER NOT NULL,
                relationship VARCHAR(64) NOT NULL,
                created_at DATETIME NOT NULL,
                UNIQUE(finding_id, observation_id, relationship)
            )
        """))
        session.commit()
    finally:
        session.close()


def ingest_evidence(
    *,
    case_id: int,
    evidence_key: str,
    payload: bytes,
    media_type: str,
    source_name: str,
    source_locator: str | None = None,
    captured_at: dt.datetime | None = None,
    metadata: dict[str, Any] | None = None,
    actor: str | None = None,
) -> dict[str, Any]:
    """Insert immutable source evidence.

    Reusing an evidence key or hash returns the existing record. Existing rows
    are never overwritten by this API.
    """
    ensure_evidence_os_schema()
    digest = _sha256_bytes(payload)
    now = _now()
    session = db.Session()
    try:
        existing = session.execute(
            text("""
                SELECT * FROM evidence_items
                WHERE case_id = :case_id
                  AND (evidence_key = :evidence_key OR sha256 = :sha256)
                ORDER BY id LIMIT 1
            """),
            {"case_id": int(case_id), "evidence_key": evidence_key, "sha256": digest},
        ).mappings().first()
        if existing:
            return {"schema": EVIDENCE_OS_SCHEMA, "created": False, "evidence": dict(existing)}

        session.execute(text("""
            INSERT INTO evidence_items
            (case_id, evidence_key, media_type, source_name, source_locator,
             captured_at, imported_at, sha256, byte_length, metadata_json, actor)
            VALUES
            (:case_id, :evidence_key, :media_type, :source_name, :source_locator,
             :captured_at, :imported_at, :sha256, :byte_length, :metadata_json, :actor)
        """), {
            "case_id": int(case_id),
            "evidence_key": evidence_key,
            "media_type": media_type,
            "source_name": source_name,
            "source_locator": source_locator,
            "captured_at": captured_at,
            "imported_at": now,
            "sha256": digest,
            "byte_length": len(payload),
            "metadata_json": _json(metadata or {}),
            "actor": actor,
        })
        session.commit()
        row = session.execute(
            text("SELECT * FROM evidence_items WHERE case_id=:case_id AND evidence_key=:evidence_key"),
            {"case_id": int(case_id), "evidence_key": evidence_key},
        ).mappings().one()
    finally:
        session.close()
    db.record_audit_event(
        action="evidence_ingested",
        actor=actor,
        details={"case_id": int(case_id), "evidence_key": evidence_key, "sha256": digest},
    )
    return {"schema": EVIDENCE_OS_SCHEMA, "created": True, "evidence": dict(row)}


def create_observation(
    *,
    case_id: int,
    evidence_item_id: int,
    observation_key: str,
    statement: str,
    classification: str = "corroborated_allegation",
    confidence: float = 0.5,
    rationale: str | None = None,
    metadata: dict[str, Any] | None = None,
    actor: str | None = None,
) -> dict[str, Any]:
    ensure_evidence_os_schema()
    if not 0.0 <= confidence <= 1.0:
        raise ValueError("confidence must be between 0 and 1")
    now = _now()
    session = db.Session()
    try:
        session.execute(text("""
            INSERT INTO evidence_observations
            (case_id, evidence_item_id, observation_key, statement, classification,
             confidence, status, rationale, metadata_json, actor, created_at, updated_at)
            VALUES
            (:case_id, :evidence_item_id, :observation_key, :statement, :classification,
             :confidence, 'proposed', :rationale, :metadata_json, :actor, :now, :now)
        """), {
            "case_id": int(case_id),
            "evidence_item_id": int(evidence_item_id),
            "observation_key": observation_key,
            "statement": statement,
            "classification": classification,
            "confidence": float(confidence),
            "rationale": rationale,
            "metadata_json": _json(metadata or {}),
            "actor": actor,
            "now": now,
        })
        session.commit()
        row = session.execute(
            text("SELECT * FROM evidence_observations WHERE case_id=:case_id AND observation_key=:key"),
            {"case_id": int(case_id), "key": observation_key},
        ).mappings().one()
    finally:
        session.close()
    return {"schema": EVIDENCE_OS_SCHEMA, "observation": dict(row)}


def review_observation(
    observation_id: int,
    *,
    decision: str,
    actor: str,
    rationale: str | None = None,
) -> dict[str, Any]:
    if decision not in {"approved", "rejected", "needs_work"}:
        raise ValueError("invalid review decision")
    ensure_evidence_os_schema()
    session = db.Session()
    try:
        session.execute(text("""
            UPDATE evidence_observations
            SET status=:decision,
                rationale=COALESCE(:rationale, rationale),
                actor=:actor,
                updated_at=:now
            WHERE id=:observation_id
        """), {
            "decision": decision,
            "rationale": rationale,
            "actor": actor,
            "now": _now(),
            "observation_id": int(observation_id),
        })
        session.commit()
        row = session.execute(
            text("SELECT * FROM evidence_observations WHERE id=:id"),
            {"id": int(observation_id)},
        ).mappings().one()
    finally:
        session.close()
    db.record_audit_event(
        action="evidence_observation_reviewed",
        actor=actor,
        details={"observation_id": int(observation_id), "decision": decision},
    )
    return {"schema": EVIDENCE_OS_SCHEMA, "observation": dict(row)}


def case_evidence_summary(case_id: int) -> dict[str, Any]:
    ensure_evidence_os_schema()
    session = db.Session()
    try:
        evidence = session.execute(
            text("SELECT * FROM evidence_items WHERE case_id=:case_id ORDER BY imported_at, id"),
            {"case_id": int(case_id)},
        ).mappings().all()
        observations = session.execute(
            text("SELECT * FROM evidence_observations WHERE case_id=:case_id ORDER BY created_at, id"),
            {"case_id": int(case_id)},
        ).mappings().all()
    finally:
        session.close()
    return {
        "schema": EVIDENCE_OS_SCHEMA,
        "case_id": int(case_id),
        "evidence_count": len(evidence),
        "observation_count": len(observations),
        "evidence": [dict(row) for row in evidence],
        "observations": [dict(row) for row in observations],
    }
