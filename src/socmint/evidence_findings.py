from __future__ import annotations

import datetime as dt
import json
from typing import Any

from sqlalchemy import bindparam, text

from . import database as db
from .evidence_os import EVIDENCE_OS_SCHEMA, ensure_evidence_os_schema

FINDINGS_SCHEMA = "socmint.evidence_findings.v39_1_0"
_ALLOWED_CLASSIFICATIONS = {
    "documented_fact",
    "corroborated_allegation",
    "reasonable_inference",
    "unresolved_question",
}
_ALLOWED_LINK_TYPES = {"supports", "contradicts", "qualifies", "context"}
_ALLOWED_TARGET_TYPES = {"claim", "proceeding", "issue", "timeline_event", "entity"}


def _now() -> dt.datetime:
    return db.utc_now()


def _json(value: Any) -> str:
    return json.dumps(value if value is not None else {}, sort_keys=True)


def ensure_findings_schema() -> None:
    ensure_evidence_os_schema()
    session = db.Session()
    try:
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS finding_targets (
                id INTEGER PRIMARY KEY,
                case_id INTEGER NOT NULL,
                finding_id INTEGER NOT NULL,
                target_type VARCHAR(64) NOT NULL,
                target_key VARCHAR(255) NOT NULL,
                relationship VARCHAR(64) NOT NULL,
                metadata_json TEXT NOT NULL,
                actor VARCHAR(255),
                created_at DATETIME NOT NULL,
                UNIQUE(finding_id, target_type, target_key, relationship)
            )
        """))
        session.commit()
    finally:
        session.close()


def create_finding(
    *,
    case_id: int,
    finding_key: str,
    statement: str,
    classification: str,
    observation_ids: list[int],
    rationale: str | None = None,
    metadata: dict[str, Any] | None = None,
    actor: str | None = None,
) -> dict[str, Any]:
    """Create a proposed finding linked to one or more observations.

    A finding can be drafted from proposed observations, but it cannot be
    approved until at least one linked supporting observation is approved.
    """
    if classification not in _ALLOWED_CLASSIFICATIONS:
        raise ValueError("invalid finding classification")
    expected_ids = {int(value) for value in observation_ids}
    if not expected_ids:
        raise ValueError("at least one observation is required")
    ensure_findings_schema()
    now = _now()
    session = db.Session()
    try:
        lookup = text("""
            SELECT id, case_id FROM evidence_observations
            WHERE id IN :ids
        """).bindparams(bindparam("ids", expanding=True))
        rows = session.execute(lookup, {"ids": sorted(expected_ids)}).mappings().all()
        found_ids = {int(row["id"]) for row in rows}
        if found_ids != expected_ids:
            raise ValueError("one or more observations do not exist")
        if any(int(row["case_id"]) != int(case_id) for row in rows):
            raise ValueError("all observations must belong to the finding case")

        session.execute(text("""
            INSERT INTO evidence_findings
            (case_id, finding_key, statement, classification, status, rationale,
             metadata_json, created_at, updated_at)
            VALUES
            (:case_id, :finding_key, :statement, :classification, 'proposed',
             :rationale, :metadata_json, :now, :now)
        """), {
            "case_id": int(case_id),
            "finding_key": finding_key,
            "statement": statement,
            "classification": classification,
            "rationale": rationale,
            "metadata_json": _json(metadata or {}),
            "now": now,
        })
        finding_id = int(session.execute(
            text("SELECT id FROM evidence_findings WHERE case_id=:case_id AND finding_key=:key"),
            {"case_id": int(case_id), "key": finding_key},
        ).scalar_one())
        for observation_id in sorted(expected_ids):
            session.execute(text("""
                INSERT INTO finding_observations
                (finding_id, observation_id, relationship, created_at)
                VALUES (:finding_id, :observation_id, 'supports', :now)
            """), {
                "finding_id": finding_id,
                "observation_id": observation_id,
                "now": now,
            })
        session.commit()
        row = session.execute(
            text("SELECT * FROM evidence_findings WHERE id=:id"),
            {"id": finding_id},
        ).mappings().one()
    finally:
        session.close()
    db.record_audit_event(
        action="evidence_finding_created",
        actor=actor,
        details={
            "case_id": int(case_id),
            "finding_key": finding_key,
            "observation_ids": sorted(expected_ids),
        },
    )
    return {"schema": FINDINGS_SCHEMA, "finding": dict(row)}


def review_finding(
    finding_id: int,
    *,
    decision: str,
    actor: str,
    rationale: str | None = None,
) -> dict[str, Any]:
    if decision not in {"approved", "rejected", "needs_work"}:
        raise ValueError("invalid review decision")
    ensure_findings_schema()
    session = db.Session()
    try:
        finding = session.execute(
            text("SELECT * FROM evidence_findings WHERE id=:id"),
            {"id": int(finding_id)},
        ).mappings().first()
        if not finding:
            raise ValueError("finding does not exist")
        if decision == "approved":
            approved_support = session.execute(text("""
                SELECT COUNT(*)
                FROM finding_observations fo
                JOIN evidence_observations eo ON eo.id = fo.observation_id
                WHERE fo.finding_id=:finding_id
                  AND fo.relationship='supports'
                  AND eo.status='approved'
            """), {"finding_id": int(finding_id)}).scalar_one()
            if int(approved_support) < 1:
                raise ValueError("finding approval requires an approved supporting observation")

        approved_by = actor if decision == "approved" else None
        approved_at = _now() if decision == "approved" else None
        session.execute(text("""
            UPDATE evidence_findings
            SET status=:decision,
                rationale=COALESCE(:rationale, rationale),
                approved_by=:approved_by,
                approved_at=:approved_at,
                updated_at=:now
            WHERE id=:finding_id
        """), {
            "decision": decision,
            "rationale": rationale,
            "approved_by": approved_by,
            "approved_at": approved_at,
            "now": _now(),
            "finding_id": int(finding_id),
        })
        session.commit()
        row = session.execute(
            text("SELECT * FROM evidence_findings WHERE id=:id"),
            {"id": int(finding_id)},
        ).mappings().one()
    finally:
        session.close()
    db.record_audit_event(
        action="evidence_finding_reviewed",
        actor=actor,
        details={"finding_id": int(finding_id), "decision": decision},
    )
    return {"schema": FINDINGS_SCHEMA, "finding": dict(row)}


def link_finding_target(
    finding_id: int,
    *,
    target_type: str,
    target_key: str,
    relationship: str = "supports",
    metadata: dict[str, Any] | None = None,
    actor: str | None = None,
) -> dict[str, Any]:
    if target_type not in _ALLOWED_TARGET_TYPES:
        raise ValueError("invalid target type")
    if relationship not in _ALLOWED_LINK_TYPES:
        raise ValueError("invalid target relationship")
    ensure_findings_schema()
    now = _now()
    session = db.Session()
    try:
        finding = session.execute(
            text("SELECT case_id FROM evidence_findings WHERE id=:id"),
            {"id": int(finding_id)},
        ).mappings().first()
        if not finding:
            raise ValueError("finding does not exist")
        session.execute(text("""
            INSERT INTO finding_targets
            (case_id, finding_id, target_type, target_key, relationship,
             metadata_json, actor, created_at)
            VALUES
            (:case_id, :finding_id, :target_type, :target_key, :relationship,
             :metadata_json, :actor, :now)
            ON CONFLICT(finding_id, target_type, target_key, relationship) DO NOTHING
        """), {
            "case_id": int(finding["case_id"]),
            "finding_id": int(finding_id),
            "target_type": target_type,
            "target_key": target_key,
            "relationship": relationship,
            "metadata_json": _json(metadata or {}),
            "actor": actor,
            "now": now,
        })
        session.commit()
        row = session.execute(text("""
            SELECT * FROM finding_targets
            WHERE finding_id=:finding_id AND target_type=:target_type
              AND target_key=:target_key AND relationship=:relationship
        """), {
            "finding_id": int(finding_id),
            "target_type": target_type,
            "target_key": target_key,
            "relationship": relationship,
        }).mappings().one()
    finally:
        session.close()
    db.record_audit_event(
        action="evidence_finding_target_linked",
        actor=actor,
        details={
            "finding_id": int(finding_id),
            "target_type": target_type,
            "target_key": target_key,
            "relationship": relationship,
        },
    )
    return {"schema": FINDINGS_SCHEMA, "target_link": dict(row)}


def finding_summary(finding_id: int) -> dict[str, Any]:
    ensure_findings_schema()
    session = db.Session()
    try:
        finding = session.execute(
            text("SELECT * FROM evidence_findings WHERE id=:id"),
            {"id": int(finding_id)},
        ).mappings().first()
        if not finding:
            raise ValueError("finding does not exist")
        observations = session.execute(text("""
            SELECT eo.*, fo.relationship
            FROM finding_observations fo
            JOIN evidence_observations eo ON eo.id = fo.observation_id
            WHERE fo.finding_id=:finding_id
            ORDER BY eo.id
        """), {"finding_id": int(finding_id)}).mappings().all()
        targets = session.execute(
            text("SELECT * FROM finding_targets WHERE finding_id=:finding_id ORDER BY id"),
            {"finding_id": int(finding_id)},
        ).mappings().all()
    finally:
        session.close()
    return {
        "schema": FINDINGS_SCHEMA,
        "evidence_os_schema": EVIDENCE_OS_SCHEMA,
        "finding": dict(finding),
        "observations": [dict(row) for row in observations],
        "targets": [dict(row) for row in targets],
    }
