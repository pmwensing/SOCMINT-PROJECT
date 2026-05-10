from __future__ import annotations

import csv
import io
import json
from collections import Counter, defaultdict
from datetime import datetime, UTC
from typing import Any

from . import database as db
from .scoring import confidence_band
from .spine_intelligence import spine_intelligence_payload

ULTIMATE_DOSSIER_SCHEMA = "socmint.ultimate_entity_human_dossier.v7_8_0"

HUMAN_IDENTIFIER_TYPES = {
    "email",
    "phone",
    "phone_country",
    "phone_carrier",
    "phone_line_type",
    "profile_url",
    "account_presence",
    "platform_presence",
    "username_claim",
    "exposure_indicator",
    "exposure_email_reference",
}

ENTITY_IDENTIFIER_TYPES = {
    "archive_snapshot",
    "external_url",
    "domain",
    "url",
    "captured_url",
    "business_profile",
    "organization_reference",
}


def _safe_json(value: str | None, fallback: Any = None) -> Any:
    if not value:
        return {} if fallback is None else fallback
    try:
        return json.loads(value)
    except Exception:
        return {} if fallback is None else fallback


def _run_id_from_source_ref(ref: str | None) -> int | None:
    parts = str(ref or "").split(":")
    if len(parts) >= 2 and parts[0] == "run":
        try:
            return int(parts[1])
        except ValueError:
            return None
    return None


def _artifacts_by_run(run_ids: set[int]) -> dict[int, list[dict[str, Any]]]:
    if not run_ids:
        return {}
    db.ensure_configured()
    session = db.Session()
    try:
        rows = (
            session.query(db.SpineRawArtifact)
            .filter(db.SpineRawArtifact.run_id.in_(run_ids))
            .order_by(db.SpineRawArtifact.created_at.desc())
            .all()
        )
        grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            grouped[row.run_id].append(
                {
                    "id": row.id,
                    "run_id": row.run_id,
                    "kind": row.kind,
                    "path": row.path,
                    "sha256": row.sha256,
                    "mime_type": row.mime_type,
                    "size_bytes": row.size_bytes,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                }
            )
        return dict(grouped)
    finally:
        session.close()


def source_traceability(subject_id: int) -> list[dict[str, Any]]:
    assertions = db.list_spine_assertions(subject_id, limit=10000)
    runs = {run.id: run for run in db.list_spine_connector_runs(subject_id=subject_id, limit=10000)}
    artifacts = _artifacts_by_run(set(runs))
    trace = []
    for assertion in assertions:
        payload = _safe_json(assertion.payload_json, {})
        source_refs = payload.get("source_refs") or []
        evidence_refs = payload.get("evidence_refs") or []
        run_ids = [_run_id_from_source_ref(ref) for ref in source_refs]
        run_ids = [run_id for run_id in run_ids if run_id in runs]
        trace.append(
            {
                "assertion_id": assertion.id,
                "assertion_type": assertion.assertion_type,
                "value": assertion.normalized_value,
                "confidence": float(assertion.confidence or 0),
                "confidence_band": confidence_band(float(assertion.confidence or 0)),
                "validation_state": assertion.validation_state,
                "source_refs": source_refs,
                "evidence_refs": evidence_refs,
                "runs": [
                    {
                        "id": run_id,
                        "connector": runs[run_id].connector_key,
                        "status": runs[run_id].status,
                        "created_at": runs[run_id].created_at.isoformat() if runs[run_id].created_at else None,
                        "artifacts": artifacts.get(run_id, []),
                    }
                    for run_id in run_ids
                ],
            }
        )
    return trace


def entity_human_resolution(assertions: list[dict[str, Any]], seeds: list[dict[str, Any]]) -> dict[str, Any]:
    identifier_types = Counter(item["type"] for item in assertions)
    confirmed = [item for item in assertions if item["validation_state"] == "confirmed"]
    high_conf = [item for item in assertions if item["confidence"] >= 0.75]
    human_signals = [item for item in assertions if item["type"] in HUMAN_IDENTIFIER_TYPES]
    entity_signals = [item for item in assertions if item["type"] in ENTITY_IDENTIFIER_TYPES]
    seed_types = {seed["type"] for seed in seeds}

    if human_signals and entity_signals:
        dossier_kind = "entity_human_hybrid"
    elif human_signals or {"email", "phone", "username"}.intersection(seed_types):
        dossier_kind = "human_subject"
    elif entity_signals or {"url"}.intersection(seed_types):
        dossier_kind = "entity_subject"
    else:
        dossier_kind = "unresolved_subject"

    confidence = 0.0
    if assertions:
        confidence = round(
            min(
                0.98,
                (len(high_conf) / max(len(assertions), 1)) * 0.55
                + (len(confirmed) / max(len(assertions), 1)) * 0.35
                + min(len(assertions), 8) * 0.0125,
            ),
            3,
        )

    contradictions = []
    for item_type, count in identifier_types.items():
        values = {item["value"] for item in assertions if item["type"] == item_type}
        if item_type in {"phone_country", "phone_carrier", "phone_line_type"} and len(values) > 1:
            contradictions.append({"type": item_type, "values": sorted(values), "count": len(values)})

    return {
        "dossier_kind": dossier_kind,
        "identity_confidence": confidence,
        "identity_band": confidence_band(confidence),
        "human_signal_count": len(human_signals),
        "entity_signal_count": len(entity_signals),
        "confirmed_count": len(confirmed),
        "high_confidence_count": len(high_conf),
        "identifier_types": dict(identifier_types),
        "contradictions": contradictions,
        "primary_identifiers": sorted({item["value"] for item in assertions if item["type"] in {"email", "phone", "profile_url", "account_presence", "platform_presence"}})[:25],
    }


def timeline(assertions: list[dict[str, Any]], runs: list[dict[str, Any]], observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    events = []
    for run in runs:
        events.append({"timestamp": run.get("created_at"), "kind": "connector_run", "label": run.get("connector"), "status": run.get("status"), "ref": f"run:{run.get('id')}"})
    for obs in observations:
        events.append({"timestamp": obs.get("created_at"), "kind": "observation", "label": obs.get("type"), "value": obs.get("value"), "ref": f"observation:{obs.get('id')}"})
    for assertion in assertions:
        events.append({"timestamp": assertion.get("updated_at") or assertion.get("created_at"), "kind": "assertion", "label": assertion.get("type"), "value": assertion.get("value"), "status": assertion.get("validation_state"), "ref": f"assertion:{assertion.get('id')}"})
    return sorted([event for event in events if event.get("timestamp")], key=lambda item: item["timestamp"])


def narrative(payload: dict[str, Any], resolution: dict[str, Any], trace: list[dict[str, Any]]) -> dict[str, Any]:
    summary = payload["summary"]
    subject = payload["subject"]
    strongest = sorted(payload["assertions"], key=lambda item: item["confidence"], reverse=True)[:5]
    gaps = []
    if not payload["assertions"]:
        gaps.append("No dossier-grade assertions have been generated yet.")
    if summary.get("diagnostic_count", 0) > summary.get("observation_count", 0):
        gaps.append("Most connector runs produced diagnostics/no-result records rather than enrichment observations.")
    if resolution["contradictions"]:
        gaps.append("Contradictory identity metadata exists and needs analyst review.")
    if not gaps:
        gaps.append("No major dossier gaps detected by automated review.")

    return {
        "executive_summary": (
            f"{subject['label']} is classified as {resolution['dossier_kind']} with "
            f"{resolution['identity_band']} identity confidence. The dossier contains "
            f"{summary['assertion_count']} assertions, {summary['observation_count']} real enrichment observations, "
            f"and {summary['connector_run_count']} connector runs."
        ),
        "key_findings": [
            f"{item['type']}: {item['value']} ({confidence_band(item['confidence'])}, {item['validation_state']})"
            for item in strongest
        ],
        "evidence_posture": f"{len(trace)} assertions have source traceability entries with connector run and artifact references where available.",
        "gaps_and_cautions": gaps,
        "recommended_next_actions": [
            "Review unreviewed assertions and confirm or reject each dossier claim.",
            "Inspect raw artifacts for any high-impact connector result before external use.",
            "Run additional seed types if identifier coverage is weak.",
            "Export the ultimate dossier package after analyst review is complete.",
        ],
    }


def ultimate_dossier_payload(subject_id: int) -> dict[str, Any]:
    intelligence = spine_intelligence_payload(subject_id)
    trace = source_traceability(subject_id)
    resolution = entity_human_resolution(intelligence["assertions"], intelligence["seeds"])
    events = timeline(intelligence["assertions"], intelligence["runs"], intelligence["observations"])
    story = narrative(intelligence, resolution, trace)
    return {
        "schema": ULTIMATE_DOSSIER_SCHEMA,
        "generated_at": datetime.now(UTC).isoformat(),
        "subject": intelligence["subject"],
        "summary": intelligence["summary"],
        "resolution": resolution,
        "narrative": story,
        "seeds": intelligence["seeds"],
        "assertions": intelligence["assertions"],
        "observations": intelligence["observations"],
        "diagnostics": intelligence["diagnostics"],
        "runs": intelligence["runs"],
        "traceability": trace,
        "timeline": events,
        "exports": {
            "html": f"/spine/subjects/{subject_id}/ultimate-dossier",
            "json": f"/api/v1/spine/subjects/{subject_id}/ultimate-dossier",
            "csv": f"/spine/subjects/{subject_id}/ultimate-dossier/assertions.csv",
        },
    }


def assertions_csv(payload: dict[str, Any]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["id", "type", "value", "confidence", "band", "validation_state", "source_count"],
    )
    writer.writeheader()
    for item in payload["assertions"]:
        writer.writerow(
            {
                "id": item["id"],
                "type": item["type"],
                "value": item["value"],
                "confidence": item["confidence"],
                "band": confidence_band(item["confidence"]),
                "validation_state": item["validation_state"],
                "source_count": item.get("payload", {}).get("source_count", ""),
            }
        )
    return output.getvalue()
