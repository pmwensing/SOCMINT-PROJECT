from __future__ import annotations

import json
from typing import Any

from . import database as db

SCHEMA = "socmint.claim_evidence_ledger.v13_5"


def _loads(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def _artifact_index(session, run_ids: set[int]) -> dict[int, list[dict[str, Any]]]:
    if not run_ids:
        return {}
    artifacts = (
        session.query(db.SpineRawArtifact)
        .filter(db.SpineRawArtifact.run_id.in_(run_ids))
        .order_by(db.SpineRawArtifact.created_at.desc())
        .all()
    )
    index: dict[int, list[dict[str, Any]]] = {}
    for artifact in artifacts:
        index.setdefault(artifact.run_id, []).append(
            {
                "artifact_id": artifact.id,
                "kind": artifact.kind,
                "path": artifact.path,
                "sha256": artifact.sha256,
                "mime_type": artifact.mime_type,
                "size_bytes": artifact.size_bytes,
            }
        )
    return index


def _assertion_rows(subject_id: int, session) -> list[dict[str, Any]]:
    rows = []
    assertions = (
        session.query(db.SpineDossierAssertion)
        .filter_by(subject_id=subject_id)
        .order_by(db.SpineDossierAssertion.created_at.desc())
        .all()
    )
    for item in assertions:
        payload = _loads(item.payload_json, {})
        evidence_refs = payload.get("evidence_refs") or payload.get("evidence") or []
        if isinstance(evidence_refs, str):
            evidence_refs = [evidence_refs]
        rows.append(
            {
                "claim_id": f"assertion:{item.id}",
                "claim_type": item.assertion_type,
                "claim_value": item.normalized_value,
                "confidence": item.confidence,
                "review_state": item.validation_state,
                "source": "spine_dossier_assertion",
                "evidence_refs": evidence_refs,
                "artifact_links": [],
                "has_evidence": bool(evidence_refs),
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
        )
    return rows


def _observation_rows(subject_id: int, session) -> list[dict[str, Any]]:
    observations = (
        session.query(db.SpineObservation)
        .filter_by(subject_id=subject_id)
        .order_by(db.SpineObservation.created_at.desc())
        .all()
    )
    run_ids = {item.run_id for item in observations if item.run_id is not None}
    artifacts_by_run = _artifact_index(session, run_ids)
    rows = []
    for item in observations:
        payload = _loads(item.payload_json, {})
        artifact_links = artifacts_by_run.get(item.run_id, [])
        evidence_refs = []
        if item.evidence_ref:
            evidence_refs.append(item.evidence_ref)
        if payload.get("evidence_ref"):
            evidence_refs.append(payload.get("evidence_ref"))
        rows.append(
            {
                "claim_id": f"observation:{item.id}",
                "claim_type": item.observation_type,
                "claim_value": item.normalized_value,
                "confidence": item.confidence,
                "review_state": "unreviewed",
                "source": item.source_ref or "spine_observation",
                "evidence_refs": evidence_refs,
                "artifact_links": artifact_links,
                "has_evidence": bool(evidence_refs or artifact_links),
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
        )
    return rows


def build_claim_evidence_ledger(subject_id: int) -> dict[str, Any]:
    db.ensure_configured()
    session = db.Session()
    try:
        subject = session.query(db.SpineSubject).filter_by(id=subject_id).first()
        if not subject:
            return {
                "schema": SCHEMA,
                "subject_id": subject_id,
                "subject_exists": False,
                "rows": [],
                "summary": {
                    "claim_count": 0,
                    "with_evidence": 0,
                    "missing_evidence": 0,
                    "unreviewed": 0,
                },
            }
        rows = [*_assertion_rows(subject_id, session), *_observation_rows(subject_id, session)]
        with_evidence = sum(1 for row in rows if row["has_evidence"])
        unreviewed = sum(1 for row in rows if row["review_state"] in {"unreviewed", "pending"})
        return {
            "schema": SCHEMA,
            "subject_id": subject_id,
            "subject_exists": True,
            "subject_label": subject.label,
            "rows": rows,
            "summary": {
                "claim_count": len(rows),
                "with_evidence": with_evidence,
                "missing_evidence": len(rows) - with_evidence,
                "unreviewed": unreviewed,
            },
        }
    finally:
        session.close()
