import json
from collections import defaultdict

from . import database as db
from .scoring import confidence_band


def _json_loads(value, default=None):
    if default is None:
        default = {}
    try:
        return json.loads(value or "{}")
    except json.JSONDecodeError:
        return default


def _parse_run_id(source_ref):
    if not source_ref:
        return None
    parts = str(source_ref).split(":")
    if len(parts) >= 2 and parts[0] == "run":
        try:
            return int(parts[1])
        except ValueError:
            return None
    return None


def explain_confidence(assertion):
    score = float(assertion.confidence or 0)
    payload = _json_loads(assertion.payload_json)
    source_count = int(payload.get("source_count") or 0)
    evidence_refs = payload.get("evidence_refs") or []
    connector_quality_delta = float(payload.get("connector_quality_delta") or 0.0)

    factors = []
    if source_count >= 3:
        factors.append("Strong source diversity: 3 or more supporting sources.")
    elif source_count == 2:
        factors.append("Moderate source diversity: 2 supporting sources.")
    elif source_count == 1:
        factors.append("Single-source lead: requires corroboration.")

    if evidence_refs:
        factors.append("Evidence references are attached to the assertion.")
    else:
        factors.append("No evidence references were attached.")

    if connector_quality_delta > 0:
        factors.append("Connector quality history increased this score.")
    elif connector_quality_delta < 0:
        factors.append("Connector rejection history reduced this score.")

    if assertion.validation_state == "confirmed":
        factors.append("Analyst confirmed this assertion.")
    elif assertion.validation_state == "rejected":
        factors.append("Analyst rejected this assertion.")
    elif assertion.validation_state == "suppressed":
        factors.append("Assertion is suppressed.")
    else:
        factors.append("Assertion has not been analyst-reviewed.")

    return {
        "score": score,
        "band": confidence_band(score),
        "source_count": source_count,
        "evidence_ref_count": len(evidence_refs),
        "validation_state": assertion.validation_state,
        "connector_quality_delta": connector_quality_delta,
        "factors": factors,
    }


def get_assertion_evidence(assertion_id):
    assertion = db.get_spine_assertion(assertion_id)
    if not assertion:
        return None

    payload = _json_loads(assertion.payload_json)
    observation_ids = payload.get("supporting_observation_ids") or []
    observations = db.get_spine_observations_by_ids(observation_ids)

    run_ids = sorted(
        {
            run_id
            for run_id in (_parse_run_id(obs.source_ref) for obs in observations)
            if run_id is not None
        }
    )
    runs = db.get_spine_connector_runs_by_ids(run_ids)

    artifacts = []
    for run in runs:
        artifacts.extend(db.list_spine_raw_artifacts(run_id=run.id))

    return {
        "assertion": {
            "id": assertion.id,
            "subject_id": assertion.subject_id,
            "type": assertion.assertion_type,
            "value": assertion.normalized_value,
            "confidence": float(assertion.confidence or 0),
            "band": confidence_band(float(assertion.confidence or 0)),
            "validation_state": assertion.validation_state,
            "payload": payload,
        },
        "confidence_explanation": explain_confidence(assertion),
        "observations": [
            {
                "id": obs.id,
                "type": obs.observation_type,
                "value": obs.normalized_value,
                "confidence": float(obs.confidence or 0),
                "source_ref": obs.source_ref,
                "evidence_ref": obs.evidence_ref,
                "payload": _json_loads(obs.payload_json),
                "created_at": obs.created_at.isoformat()
                if obs.created_at
                else None,
            }
            for obs in observations
        ],
        "connector_runs": [
            {
                "id": run.id,
                "subject_id": run.subject_id,
                "connector": run.connector_key,
                "seed_id": run.seed_id,
                "status": run.status,
                "created_at": run.created_at.isoformat()
                if run.created_at
                else None,
            }
            for run in runs
        ],
        "raw_artifacts": [
            {
                "id": artifact.id,
                "run_id": artifact.run_id,
                "kind": artifact.kind,
                "path": artifact.path,
                "sha256": artifact.sha256,
                "mime_type": artifact.mime_type,
                "size_bytes": artifact.size_bytes,
                "created_at": artifact.created_at.isoformat()
                if artifact.created_at
                else None,
            }
            for artifact in artifacts
        ],
    }


def connector_quality_metrics():
    runs = db.list_spine_connector_runs(limit=10000)
    observations = db.list_all_spine_observations(limit=10000)
    assertions = db.list_all_spine_assertions(limit=10000)

    by_connector = defaultdict(
        lambda: {
            "connector": None,
            "runs": 0,
            "successes": 0,
            "failures": 0,
            "dry_runs": 0,
            "observations": 0,
            "assertions": 0,
            "confirmed_assertions": 0,
            "rejected_assertions": 0,
            "suppressed_assertions": 0,
            "confidence_total": 0.0,
            "confidence_count": 0,
            "artifact_refs": 0,
        }
    )

    run_connector = {}
    for run in runs:
        item = by_connector[run.connector_key]
        item["connector"] = run.connector_key
        item["runs"] += 1
        run_connector[run.id] = run.connector_key

        status = (run.status or "").lower()
        if status in {"completed", "succeeded", "success"}:
            item["successes"] += 1
        elif status == "dry_run":
            item["dry_runs"] += 1
        elif status in {"failed", "timeout", "error"}:
            item["failures"] += 1

    for obs in observations:
        run_id = _parse_run_id(obs.source_ref)
        connector = run_connector.get(run_id)
        if not connector:
            continue
        item = by_connector[connector]
        item["observations"] += 1
        if obs.evidence_ref:
            item["artifact_refs"] += 1
        item["confidence_total"] += float(obs.confidence or 0)
        item["confidence_count"] += 1

    for assertion in assertions:
        payload = _json_loads(assertion.payload_json)
        source_refs = payload.get("source_refs") or []
        connectors = set()
        for ref in source_refs:
            run_id = _parse_run_id(ref)
            if run_id in run_connector:
                connectors.add(run_connector[run_id])

        for connector in connectors:
            item = by_connector[connector]
            item["assertions"] += 1
            if assertion.validation_state == "confirmed":
                item["confirmed_assertions"] += 1
            elif assertion.validation_state == "rejected":
                item["rejected_assertions"] += 1
            elif assertion.validation_state == "suppressed":
                item["suppressed_assertions"] += 1

    result = []
    for item in by_connector.values():
        count = item.pop("confidence_count")
        total = item.pop("confidence_total")
        item["average_confidence"] = round(total / count, 3) if count else 0.0
        item["evidence_coverage"] = (
            round(item["artifact_refs"] / item["observations"], 3)
            if item["observations"]
            else 0.0
        )
        item["rejection_rate"] = (
            round(item["rejected_assertions"] / item["assertions"], 3)
            if item["assertions"]
            else 0.0
        )
        result.append(item)

    return sorted(result, key=lambda row: row["connector"] or "")
