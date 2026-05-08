import json

from . import database as db
from .media_profile import enrich_url_observation


def _json_loads(value, default=None):
    if default is None:
        default = {}
    try:
        return json.loads(value or "{}")
    except json.JSONDecodeError:
        return default


def enrich_subject_media_profiles(subject_id: int) -> dict:
    if not db.get_spine_subject(subject_id):
        raise ValueError("Subject not found.")

    created = []
    for obs in db.list_spine_observations(subject_id):
        value = obs.normalized_value or ""
        if not value.startswith(("http://", "https://")):
            continue

        result = enrich_url_observation(value)
        artifact = result.get("artifact") or {}
        enrichment_type = result.get("adapter", "profile_media_enrichment")
        enrichment_id = db.create_media_profile_enrichment(
            subject_id=subject_id,
            observation_id=obs.id,
            enrichment_type=enrichment_type,
            status=result.get("status", "unknown"),
            source_value=value,
            artifact_ref=artifact.get("sha256"),
            payload=result,
        )
        created.append(enrichment_id)

        for finding in result.get("findings", []):
            db.create_spine_observation(
                subject_id=subject_id,
                run_id=obs.run_id,
                observation_type=finding.get("type", "enrichment_finding"),
                normalized_value=str(finding.get("value", "")),
                confidence=str(finding.get("confidence", 0.5)),
                source_ref=f"enrichment:{enrichment_id}:{enrichment_type}",
                evidence_ref=f"sha256:{artifact.get('sha256')}"
                if artifact.get("sha256")
                else obs.evidence_ref,
                payload=finding,
            )

    return {"subject_id": subject_id, "enrichment_ids": created}


def media_profile_payload(subject_id: int) -> dict:
    enrichments = db.list_media_profile_enrichments(subject_id)
    return {
        "subject_id": subject_id,
        "enrichments": [
            {
                "id": item.id,
                "observation_id": item.observation_id,
                "type": item.enrichment_type,
                "status": item.status,
                "source_value": item.source_value,
                "artifact_ref": item.artifact_ref,
                "payload": _json_loads(item.payload_json),
                "created_at": item.created_at.isoformat()
                if item.created_at
                else None,
            }
            for item in enrichments
        ],
    }



def enrich_dossier(dossier):
    """Backward-compatible enrichment hook for legacy CLI generation.

    The v6+ production spine uses subject-level enrichment via
    enrich_subject_media_profiles().  The older CLI path still imports and
    calls enrich_dossier(), so keep this lightweight compatibility wrapper to
    prevent dashboard startup/import failures.
    """
    if not isinstance(dossier, dict):
        return dossier

    enriched = dict(dossier)
    enriched.setdefault("enrichment", {})
    enriched["enrichment"].setdefault("status", "legacy_compat")
    enriched["enrichment"].setdefault(
        "note",
        "Use the v6+ dossier spine/workbench for production enrichment.",
    )
    return enriched
