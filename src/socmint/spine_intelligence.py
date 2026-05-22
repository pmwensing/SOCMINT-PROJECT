from __future__ import annotations

import json
from typing import Any

from . import database as db
from .alias_promotion_gates_v12_10_7_1 import apply_promotion_gates_to_observation, promotion_gate_for_observation
from .legacy_assertion_scrubber_v12_10_7_2 import apply_assertion_scrub_gate
from .spine import DIAGNOSTIC_OBSERVATION_TYPES
from .spine import HIGH_VALUE_CONNECTORS

INTELLIGENCE_SCHEMA = "socmint.spine_intelligence.v7_7_1"
VALID_ASSERTION_ACTIONS = {"confirmed", "rejected", "suppressed", "unreviewed"}


def _safe_json(value: str | None, fallback: Any = None) -> Any:
    if not value:
        return {} if fallback is None else fallback
    try:
        return json.loads(value)
    except Exception:
        return {} if fallback is None else fallback


def _connector_options(seeds: list) -> list[dict[str, Any]]:
    seed_types = {seed.seed_type for seed in seeds}
    options = []
    for key, spec in HIGH_VALUE_CONNECTORS.items():
        compatible = sorted(seed_types.intersection(set(spec["seed_types"])))
        options.append(
            {
                "key": key,
                "seed_types": spec["seed_types"],
                "compatible": compatible,
                "enabled": bool(compatible),
                "base_confidence": spec["base"],
            }
        )
    return options


def _serialize_seed(seed) -> dict[str, Any]:
    return {
        "id": seed.id,
        "type": seed.seed_type,
        "raw_value": seed.raw_value,
        "value": seed.normalized_value,
        "hash": seed.pii_hash,
        "created_at": seed.created_at.isoformat() if seed.created_at else None,
    }


def _serialize_run(run, artifacts_by_run: dict[int, list[dict[str, Any]]]) -> dict[str, Any]:
    raw = _safe_json(run.raw_result_json, {})
    result = raw.get("result", {}) if isinstance(raw, dict) else {}
    findings = result.get("findings", []) if isinstance(result, dict) else []
    return {
        "id": run.id,
        "subject_id": run.subject_id,
        "connector": run.connector_key,
        "seed_id": run.seed_id,
        "status": run.status,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "raw_result": raw,
        "stdout": result.get("stdout", "") if isinstance(result, dict) else "",
        "stderr": result.get("stderr", "") if isinstance(result, dict) else "",
        "findings": findings,
        "finding_count": len(findings),
        "artifacts": artifacts_by_run.get(run.id, []),
    }


def _serialize_artifact(artifact) -> dict[str, Any]:
    return {
        "id": artifact.id,
        "run_id": artifact.run_id,
        "kind": artifact.kind,
        "path": artifact.path,
        "sha256": artifact.sha256,
        "mime_type": artifact.mime_type,
        "size_bytes": artifact.size_bytes,
        "meta": _safe_json(artifact.meta_json, {}),
        "created_at": artifact.created_at.isoformat() if artifact.created_at else None,
    }


def _serialize_observation(observation) -> dict[str, Any]:
    payload = _safe_json(observation.payload_json, {})
    diagnostic = observation.observation_type in DIAGNOSTIC_OBSERVATION_TYPES or bool(payload.get("diagnostic"))
    item = {
        "id": observation.id,
        "subject_id": observation.subject_id,
        "run_id": observation.run_id,
        "type": observation.observation_type,
        "value": observation.normalized_value,
        "confidence": float(observation.confidence or 0),
        "source_ref": observation.source_ref,
        "evidence_ref": observation.evidence_ref,
        "payload": payload,
        "diagnostic": diagnostic,
        "created_at": observation.created_at.isoformat() if observation.created_at else None,
    }
    return apply_promotion_gates_to_observation(item)


def _serialize_assertion(assertion) -> dict[str, Any]:
    payload = _safe_json(assertion.payload_json, {})
    item = {
        "id": assertion.id,
        "subject_id": assertion.subject_id,
        "type": assertion.assertion_type,
        "value": assertion.normalized_value,
        "confidence": float(assertion.confidence or 0),
        "validation_state": assertion.validation_state,
        "payload": payload,
        "created_at": assertion.created_at.isoformat() if assertion.created_at else None,
        "updated_at": assertion.updated_at.isoformat() if assertion.updated_at else None,
    }
    return apply_assertion_scrub_gate(item)


def _artifacts_by_run(subject_run_ids: set[int]) -> dict[int, list[dict[str, Any]]]:
    if not subject_run_ids:
        return {}
    db.ensure_configured()
    session = db.Session()
    try:
        rows = (
            session.query(db.SpineRawArtifact)
            .filter(db.SpineRawArtifact.run_id.in_(subject_run_ids))
            .order_by(db.SpineRawArtifact.created_at.desc())
            .all()
        )
        grouped: dict[int, list[dict[str, Any]]] = {}
        for row in rows:
            grouped.setdefault(row.run_id, []).append(_serialize_artifact(row))
        return grouped
    finally:
        session.close()


def spine_intelligence_payload(subject_id: int) -> dict[str, Any]:
    subject = db.get_spine_subject(subject_id)
    if not subject:
        raise ValueError("Subject not found.")

    seeds = db.list_spine_seeds(subject_id)
    runs = db.list_spine_connector_runs(subject_id=subject_id, limit=1000)
    observations = db.list_spine_observations(subject_id, limit=5000)
    assertions = db.list_spine_assertions(subject_id, limit=5000)
    artifacts = _artifacts_by_run({run.id for run in runs})

    serialized_observations = [_serialize_observation(item) for item in observations]
    enrichment_observations = [item for item in serialized_observations if not item["diagnostic"]]
    diagnostics = [item for item in serialized_observations if item["diagnostic"]]
    serialized_assertions = [_serialize_assertion(item) for item in assertions]
    validated = [item for item in serialized_assertions if item["validation_state"] == "confirmed"]
    rejected = [item for item in serialized_assertions if item["validation_state"] == "rejected"]
    unreviewed = [item for item in serialized_assertions if item["validation_state"] == "unreviewed"]

    summary = {
        "seed_count": len(seeds),
        "connector_run_count": len(runs),
        "artifact_count": sum(len(items) for items in artifacts.values()),
        "observation_count": len(enrichment_observations),
        "diagnostic_count": len(diagnostics),
        "raw_observation_count": len(serialized_observations),
        "assertion_count": len(assertions),
        "confirmed_assertions": len(validated),
        "rejected_assertions": len(rejected),
        "unreviewed_assertions": len(unreviewed),
        "dossier_ready": bool(assertions),
        "needs_review": bool(unreviewed),
        "has_real_enrichment": bool(enrichment_observations or assertions),
    }

    return {
        "schema": INTELLIGENCE_SCHEMA,
        "subject": {
            "id": subject.id,
            "label": subject.label or f"Subject {subject.id}",
            "created_at": subject.created_at.isoformat() if subject.created_at else None,
        },
        "summary": summary,
        "seeds": [_serialize_seed(seed) for seed in seeds],
        "connector_options": _connector_options(seeds),
        "runs": [_serialize_run(run, artifacts) for run in runs],
        "observations": enrichment_observations,
        "diagnostics": diagnostics,
        "assertions": serialized_assertions,
        "dossier_url": f"/spine/subjects/{subject_id}/dossier",
        "classic_subject_url": f"/spine/{subject_id}",
        "full_report_url": f"/spine/subjects/{subject_id}/full-report/view",
        "export_history_url": f"/spine/subjects/{subject_id}/full-report/history",
    }


def promote_observation_to_assertion(observation_id: int, actor: str | None = None, note: str | None = None) -> dict[str, Any]:
    observation = db.get_spine_observation(observation_id)
    if not observation:
        raise LookupError("Observation not found.")
    payload = _serialize_observation(observation)
    if payload["diagnostic"]:
        raise ValueError("Diagnostic observations cannot be promoted to dossier assertions.")

    gate = promotion_gate_for_observation(payload)
    if gate["blocked"]:
        reasons = ", ".join(gate.get("reason_labels") or [])
        raise ValueError(f"{gate['ui_badge']}: {reasons}")

    assertion_id = db.upsert_spine_assertion(
        subject_id=observation.subject_id,
        assertion_type=gate.get("safe_type") or observation.observation_type,
        normalized_value=observation.normalized_value,
        confidence=str(observation.confidence or 0.5),
        validation_state="confirmed",
        payload={
            "source": "spine_observation_promotion",
            "observation": payload,
            "promotion_gate": gate,
            "actor": actor,
            "note": note,
        },
    )
    db.record_audit_event(
        "spine_observation_promote",
        actor=actor,
        details={
            "observation_id": observation_id,
            "assertion_id": assertion_id,
            "subject_id": observation.subject_id,
            "note": note,
        },
    )
    return {
        "schema": INTELLIGENCE_SCHEMA,
        "observation_id": observation_id,
        "assertion_id": assertion_id,
        "subject_id": observation.subject_id,
        "validation_state": "confirmed",
    }


def review_spine_assertion(assertion_id: int, action: str, actor: str | None = None, note: str | None = None) -> dict[str, Any]:
    action = (action or "").strip().lower()
    if action not in VALID_ASSERTION_ACTIONS:
        raise ValueError("Invalid assertion review action.")
    updated_id = db.validate_spine_assertion(assertion_id, actor, action, note)
    if not updated_id:
        raise LookupError("Assertion not found.")
    db.record_audit_event(
        "spine_intelligence_assertion_review",
        actor=actor,
        details={"assertion_id": assertion_id, "action": action, "note": note},
    )
    return {
        "schema": INTELLIGENCE_SCHEMA,
        "assertion_id": assertion_id,
        "validation_state": action,
    }
