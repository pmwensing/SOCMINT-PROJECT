from __future__ import annotations

import json
from typing import Any

from . import database as db

REVIEW_SCHEMA = "socmint.connector_review.v7_6_2"
VALID_ACTIONS = {"promote", "reject", "uncertain"}


def _safe_json(value: str | None, fallback: Any = None) -> Any:
    if not value:
        return {} if fallback is None else fallback
    try:
        return json.loads(value)
    except Exception:
        return {} if fallback is None else fallback


def _serialize_run(run) -> dict[str, Any]:
    raw = _safe_json(run.raw_result, {})
    return {
        "id": run.id,
        "target_id": run.target_id,
        "target_value": run.target_value,
        "target_type": run.target_type,
        "connector": run.connector,
        "status": run.status,
        "command": _safe_json(run.command, []),
        "error": run.error,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "raw_result": raw,
        "stdout": raw.get("stdout", "") if isinstance(raw, dict) else "",
        "stderr": raw.get("stderr", "") if isinstance(raw, dict) else "",
        "normalized_findings": raw.get("findings", []) if isinstance(raw, dict) else [],
    }


def _serialize_finding(finding, run=None) -> dict[str, Any]:
    context = _safe_json(finding.context, {})
    payload = {
        "id": finding.id,
        "connector_run_id": finding.connector_run_id,
        "target_id": finding.target_id,
        "source": finding.source,
        "type": finding.type,
        "value": finding.value,
        "confidence": finding.confidence,
        "context": context,
        "created_at": finding.created_at.isoformat() if finding.created_at else None,
    }
    if run is not None:
        payload["run"] = {
            "id": run.id,
            "connector": run.connector,
            "target_value": run.target_value,
            "target_type": run.target_type,
            "status": run.status,
        }
    return payload


def connector_runs_payload(limit: int = 100) -> dict[str, Any]:
    runs = db.list_connector_runs(limit=limit)
    return {
        "schema": REVIEW_SCHEMA,
        "count": len(runs),
        "runs": [_serialize_run(run) for run in runs],
    }


def connector_run_detail_payload(run_id: int) -> dict[str, Any] | None:
    db.ensure_configured()
    session = db.Session()
    try:
        run = session.query(db.ConnectorRun).filter_by(id=run_id).first()
        if not run:
            return None
        findings = (
            session.query(db.Finding)
            .filter_by(connector_run_id=run_id)
            .order_by(db.Finding.created_at.desc())
            .all()
        )
        subjects = db.list_spine_subjects(limit=100)
        return {
            "schema": REVIEW_SCHEMA,
            "run": _serialize_run(run),
            "findings": [_serialize_finding(item) for item in findings],
            "subjects": [
                {"id": subject.id, "label": subject.label or f"Subject {subject.id}"}
                for subject in subjects
            ],
        }
    finally:
        session.close()


def finding_queue_payload(limit: int = 200) -> dict[str, Any]:
    db.ensure_configured()
    session = db.Session()
    try:
        findings = (
            session.query(db.Finding, db.ConnectorRun)
            .join(db.ConnectorRun, db.Finding.connector_run_id == db.ConnectorRun.id)
            .order_by(db.Finding.created_at.desc())
            .limit(limit)
            .all()
        )
        subjects = db.list_spine_subjects(limit=100)
        return {
            "schema": REVIEW_SCHEMA,
            "count": len(findings),
            "findings": [_serialize_finding(finding, run) for finding, run in findings],
            "subjects": [
                {"id": subject.id, "label": subject.label or f"Subject {subject.id}"}
                for subject in subjects
            ],
        }
    finally:
        session.close()


def review_finding(finding_id: int, action: str, actor: str | None = None, note: str | None = None, subject_id: int | None = None) -> dict[str, Any]:
    action = (action or "").strip().lower()
    if action not in VALID_ACTIONS:
        raise ValueError("Invalid finding review action.")

    db.ensure_configured()
    session = db.Session()
    try:
        finding = session.query(db.Finding).filter_by(id=finding_id).first()
        if not finding:
            raise LookupError("Finding not found.")
        run = session.query(db.ConnectorRun).filter_by(id=finding.connector_run_id).first()
        finding_payload = _serialize_finding(finding, run)
    finally:
        session.close()

    assertion_id = None
    validation_state = "unreviewed"
    if action == "promote" and subject_id:
        assertion_id = db.upsert_spine_assertion(
            subject_id=subject_id,
            assertion_type=finding_payload["type"],
            normalized_value=finding_payload["value"],
            confidence=finding_payload["confidence"],
            validation_state="confirmed",
            payload={
                "source": "connector_finding_promotion",
                "finding": finding_payload,
                "note": note,
                "actor": actor,
            },
        )
        validation_state = "confirmed"
    elif action == "reject":
        validation_state = "rejected"
    elif action == "uncertain":
        validation_state = "uncertain"

    db.record_audit_event(
        "connector_finding_review",
        actor=actor,
        target=None,
        details={
            "finding_id": finding_id,
            "action": action,
            "subject_id": subject_id,
            "assertion_id": assertion_id,
            "validation_state": validation_state,
            "note": note,
        },
    )
    return {
        "schema": REVIEW_SCHEMA,
        "finding_id": finding_id,
        "action": action,
        "subject_id": subject_id,
        "assertion_id": assertion_id,
        "validation_state": validation_state,
    }
