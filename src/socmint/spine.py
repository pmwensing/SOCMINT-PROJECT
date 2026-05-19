import json
from collections import defaultdict
from datetime import datetime, UTC

from . import database as db
from .archivebox_adapter import capture_url
from .artifacts import write_json_artifact
from .connector_normalizers import normalize_connector_output
from .scoring import confidence_band, score_observation
from .seeds import normalize_seed


HIGH_VALUE_CONNECTORS = {
    "maigret": {"seed_types": ["username", "email"], "base": 0.56},
    "sherlock": {"seed_types": ["username", "email"], "base": 0.54},
    "socialscan": {"seed_types": ["username", "email"], "base": 0.62},
    "social-analyzer": {"seed_types": ["username", "email"], "base": 0.74, "deep_enrichment": True},
    "holehe": {"seed_types": ["email"], "base": 0.56},
    "h8mail": {"seed_types": ["email"], "base": 0.58},
    "phoneinfoga": {"seed_types": ["phone"], "base": 0.65},
    "archivebox": {"seed_types": ["url"], "base": 0.82},
}

DIAGNOSTIC_OBSERVATION_TYPES = {
    "archive_candidate",
    "connector_no_result",
    "seed_expansion_candidate",
}
NON_ENRICHMENT_STATUSES = {"dry_run", "skipped", "timeout", "failed"}
SEED_ECHO_FINDING_TYPES = {"email", "username", "seed", "target", "archive_candidate", "url"}


def create_subject(label: str | None, seeds: list[dict]) -> int:
    subject_id = db.create_spine_subject(label=label)
    for seed in seeds:
        normalized = normalize_seed(seed.get("value", ""), seed.get("type") or None)
        db.add_spine_seed(subject_id=subject_id, seed_type=normalized.seed_type, raw_value=normalized.raw_value, normalized_value=normalized.normalized_value, pii_hash=normalized.pii_hash)
    return subject_id


def run_spine_for_subject(subject_id: int, connectors: list[str] | None = None) -> dict:
    if not db.get_spine_subject(subject_id):
        raise ValueError("Subject not found.")
    selected = connectors or list(HIGH_VALUE_CONNECTORS)
    run_ids = []
    for seed in db.list_spine_seeds(subject_id):
        for key in selected:
            spec = HIGH_VALUE_CONNECTORS.get(key)
            if not spec or seed.seed_type not in spec["seed_types"]:
                continue
            run_ids.append(run_connector_for_seed(subject_id, seed, key, spec))
    correlate_subject(subject_id)
    try:
        from .account_discovery import ingest_account_discoveries
        ingest_account_discoveries(subject_id, actor="spine", capture_profiles=False)
    except Exception:
        pass
    return {"subject_id": subject_id, "run_ids": run_ids}


def run_connector_for_seed(subject_id: int, seed, connector_key: str, spec: dict) -> int:
    result = execute_connector(connector_key, seed)
    status = result.get("status", "completed")
    payload = {"connector": connector_key, "seed_type": seed.seed_type, "seed_hash": seed.pii_hash, "result": result, "created_at": datetime.now(UTC).isoformat()}
    artifact = write_json_artifact("connector-runs", payload, prefix=f"{connector_key}-{subject_id}")
    run_id = db.create_spine_connector_run(subject_id=subject_id, connector_key=connector_key, seed_id=seed.id, status=status, raw_result=payload)
    db.create_spine_raw_artifact(run_id=run_id, kind=artifact["kind"], path=artifact["path"], sha256=artifact["sha256"], mime_type=artifact["mime_type"], size_bytes=artifact["size_bytes"], meta=payload)
    for observation in extract_observations(connector_key, seed, result, spec, artifact):
        db.create_spine_observation(subject_id=subject_id, run_id=run_id, observation_type=observation["type"], normalized_value=observation["value"], confidence=str(observation["confidence"]), source_ref=f"run:{run_id}:{connector_key}", evidence_ref=f"sha256:{artifact['sha256']}", payload=observation)
    return run_id


def execute_connector(connector_key: str, seed) -> dict:
    if connector_key == "archivebox":
        return capture_url(seed.normalized_value)
    if connector_key == "social-analyzer":
        from .social_analyzer_connector_v12_10_2 import run_social_analyzer
        return run_social_analyzer(seed.normalized_value, seed.seed_type, allow_dry_run=True)
    try:
        from .connectors import run_connector
        return run_connector(connector_key, seed.normalized_value, seed.seed_type, allow_dry_run=True)
    except Exception as exc:
        return {"connector": connector_key, "status": "dry_run", "stderr": str(exc), "findings": []}


def _parse_run_id(source_ref):
    parts = str(source_ref or "").split(":")
    if len(parts) >= 2 and parts[0] == "run":
        try:
            return int(parts[1])
        except ValueError:
            return None
    return None


def _same_as_seed(value, seed) -> bool:
    return str(value or "").lower().strip() == str(seed.normalized_value or "").lower().strip()


def extract_observations(connector_key, seed, raw_result, spec, artifact) -> list[dict]:
    observations = []
    status = str(raw_result.get("status") or "").strip().lower()
    normalized_findings = normalize_connector_output(connector_key, seed.normalized_value, seed.seed_type, raw_result)
    for finding in normalized_findings:
        value = str(finding.get("value") or "").strip()
        finding_type = str(finding.get("type", "connector_finding")).strip()
        if not value:
            continue
        diagnostic = status in NON_ENRICHMENT_STATUSES and (_same_as_seed(value, seed) or finding_type in SEED_ECHO_FINDING_TYPES)
        observations.append({"type": finding_type, "value": value, "connector": connector_key, "seed_type": seed.seed_type, "seed_hash": seed.pii_hash, "confidence": float(finding.get("confidence", spec["base"])), "artifact_sha256": artifact["sha256"], "payload": finding, "diagnostic": diagnostic, "deep_enrichment": bool(spec.get("deep_enrichment")), "normalizer_schema": "socmint.connector_normalizers.v12_10_2"})
    if not observations:
        observations.append({"type": "connector_no_result", "value": f"{connector_key}:{seed.seed_type}", "connector": connector_key, "seed_type": seed.seed_type, "seed_hash": seed.pii_hash, "confidence": 0.05, "artifact_sha256": artifact["sha256"], "payload": raw_result, "diagnostic": True, "deep_enrichment": bool(spec.get("deep_enrichment")), "note": "Connector completed but produced no normalized enrichment findings for this seed."})
    return observations


def connector_quality_adjustments() -> dict:
    runs = db.list_spine_connector_runs(limit=10000)
    assertions = db.list_all_spine_assertions(limit=10000)
    run_connectors = {run.id: run.connector_key for run in runs}
    stats = defaultdict(lambda: {"confirmed": 0, "rejected": 0})
    for assertion in assertions:
        payload = json.loads(assertion.payload_json or "{}")
        connectors = set()
        for ref in payload.get("source_refs") or []:
            connector = run_connectors.get(_parse_run_id(ref))
            if connector:
                connectors.add(connector)
        for connector in connectors:
            if assertion.validation_state == "rejected":
                stats[connector]["rejected"] += 1
            elif assertion.validation_state == "confirmed":
                stats[connector]["confirmed"] += 1
    adjustments = {}
    for connector, item in stats.items():
        reviewed = item["confirmed"] + item["rejected"]
        if not reviewed:
            continue
        rejection_rate = item["rejected"] / reviewed
        confirmation_rate = item["confirmed"] / reviewed
        adjustments[connector] = round(min(0.05, confirmation_rate * 0.05) - min(0.18, rejection_rate * 0.18), 3)
    return adjustments


def correlate_subject(subject_id: int) -> list[int]:
    grouped = defaultdict(list)
    quality_adjustments = connector_quality_adjustments()
    runs = db.list_spine_connector_runs(subject_id=subject_id, limit=10000)
    run_connectors = {run.id: run.connector_key for run in runs}
    for obs in db.list_spine_observations(subject_id):
        if obs.observation_type in DIAGNOSTIC_OBSERVATION_TYPES:
            continue
        key = (obs.observation_type, (obs.normalized_value or "").lower().strip())
        grouped[key].append(obs)
    assertion_ids = []
    for (obs_type, value), group in grouped.items():
        if not value:
            continue
        source_count = len({item.source_ref for item in group})
        archived = any("archive" in item.observation_type for item in group)
        base = max(float(item.confidence or 0.5) for item in group)
        connectors = {run_connectors[run_id] for run_id in (_parse_run_id(item.source_ref) for item in group) if run_id in run_connectors}
        quality_delta = round(sum(quality_adjustments.get(connector, 0.0) for connector in connectors) / len(connectors), 3) if connectors else 0.0
        score = score_observation(base=base, source_count=source_count, archived=archived, exact_identifier_match=source_count >= 2, connector_quality_delta=quality_delta)
        payload = {"assertion_type": obs_type, "value": value, "confidence": score, "confidence_band": confidence_band(score), "source_count": source_count, "supporting_observation_ids": [item.id for item in group], "source_refs": [item.source_ref for item in group], "evidence_refs": [item.evidence_ref for item in group], "connector_quality_delta": quality_delta, "connectors": sorted(connectors)}
        assertion_ids.append(db.upsert_spine_assertion(subject_id=subject_id, assertion_type=obs_type, normalized_value=value, confidence=str(score), validation_state="unreviewed", payload=payload))
    return assertion_ids
