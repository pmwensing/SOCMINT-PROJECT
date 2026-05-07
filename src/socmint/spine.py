import json
from collections import defaultdict
from datetime import datetime, UTC

from . import database as db
from .archivebox_adapter import capture_url
from .artifacts import write_json_artifact
from .scoring import confidence_band, score_observation
from .seeds import normalize_seed


HIGH_VALUE_CONNECTORS = {
    "maigret": {"seed_types": ["username", "email"], "base": 0.56},
    "sherlock": {"seed_types": ["username", "email"], "base": 0.54},
    "socialscan": {"seed_types": ["username", "email"], "base": 0.62},
    "holehe": {"seed_types": ["email"], "base": 0.56},
    "h8mail": {"seed_types": ["email"], "base": 0.58},
    "phoneinfoga": {"seed_types": ["phone"], "base": 0.65},
    "archivebox": {"seed_types": ["url"], "base": 0.82},
}


def create_subject(label: str | None, seeds: list[dict]) -> int:
    subject_id = db.create_spine_subject(label=label)
    for seed in seeds:
        normalized = normalize_seed(
            seed.get("value", ""),
            seed.get("type") or None,
        )
        db.add_spine_seed(
            subject_id=subject_id,
            seed_type=normalized.seed_type,
            raw_value=normalized.raw_value,
            normalized_value=normalized.normalized_value,
            pii_hash=normalized.pii_hash,
        )
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
    return {"subject_id": subject_id, "run_ids": run_ids}


def run_connector_for_seed(
    subject_id: int,
    seed,
    connector_key: str,
    spec: dict,
) -> int:
    result = execute_connector(connector_key, seed)
    status = result.get("status", "completed")

    payload = {
        "connector": connector_key,
        "seed_type": seed.seed_type,
        "seed_hash": seed.pii_hash,
        "result": result,
        "created_at": datetime.now(UTC).isoformat(),
    }

    artifact = write_json_artifact(
        "connector-runs",
        payload,
        prefix=f"{connector_key}-{subject_id}",
    )

    run_id = db.create_spine_connector_run(
        subject_id=subject_id,
        connector_key=connector_key,
        seed_id=seed.id,
        status=status,
        raw_result=payload,
    )

    db.create_spine_raw_artifact(
        run_id=run_id,
        kind=artifact["kind"],
        path=artifact["path"],
        sha256=artifact["sha256"],
        mime_type=artifact["mime_type"],
        size_bytes=artifact["size_bytes"],
        meta=payload,
    )

    observations = extract_observations(
        connector_key,
        seed,
        result,
        spec,
        artifact,
    )
    for observation in observations:
        db.create_spine_observation(
            subject_id=subject_id,
            run_id=run_id,
            observation_type=observation["type"],
            normalized_value=observation["value"],
            confidence=str(observation["confidence"]),
            source_ref=f"run:{run_id}:{connector_key}",
            evidence_ref=f"sha256:{artifact['sha256']}",
            payload=observation,
        )

    return run_id


def execute_connector(connector_key: str, seed) -> dict:
    if connector_key == "archivebox":
        return capture_url(seed.normalized_value)

    try:
        from .connectors import run_connector

        return run_connector(
            connector_key,
            seed.normalized_value,
            seed.seed_type,
            allow_dry_run=True,
        )
    except Exception as exc:
        return {
            "connector": connector_key,
            "status": "dry_run",
            "stderr": str(exc),
            "findings": [],
        }


def extract_observations(connector_key, seed, raw_result, spec, artifact) -> list[dict]:
    observations = []
    findings = raw_result.get("findings", []) if isinstance(raw_result, dict) else []

    for finding in findings:
        value = str(finding.get("value") or finding.get("url") or "").strip()
        if not value:
            continue
        observations.append(
            {
                "type": finding.get("type", "connector_finding"),
                "value": value,
                "connector": connector_key,
                "seed_type": seed.seed_type,
                "seed_hash": seed.pii_hash,
                "confidence": float(finding.get("confidence", spec["base"])),
                "artifact_sha256": artifact["sha256"],
                "payload": finding,
            }
        )

    if not observations:
        observations.append(
            {
                "type": "seed_expansion_candidate",
                "value": seed.normalized_value,
                "connector": connector_key,
                "seed_type": seed.seed_type,
                "seed_hash": seed.pii_hash,
                "confidence": spec["base"],
                "artifact_sha256": artifact["sha256"],
                "payload": raw_result,
            }
        )

    return observations


def correlate_subject(subject_id: int) -> list[int]:
    grouped = defaultdict(list)
    for obs in db.list_spine_observations(subject_id):
        key = (obs.observation_type, (obs.normalized_value or "").lower().strip())
        grouped[key].append(obs)

    assertion_ids = []
    for (obs_type, value), group in grouped.items():
        if not value:
            continue

        source_count = len({item.source_ref for item in group})
        archived = any("archive" in item.observation_type for item in group)
        base = max(float(item.confidence or 0.5) for item in group)
        score = score_observation(
            base=base,
            source_count=source_count,
            archived=archived,
            exact_identifier_match=source_count >= 2,
        )

        payload = {
            "assertion_type": obs_type,
            "value": value,
            "confidence": score,
            "confidence_band": confidence_band(score),
            "source_count": source_count,
            "supporting_observation_ids": [item.id for item in group],
            "source_refs": [item.source_ref for item in group],
            "evidence_refs": [item.evidence_ref for item in group],
        }

        assertion_ids.append(
            db.upsert_spine_assertion(
                subject_id=subject_id,
                assertion_type=obs_type,
                normalized_value=value,
                confidence=str(score),
                validation_state="unreviewed",
                payload=payload,
            )
        )

    return assertion_ids


def build_dossier(subject_id: int) -> dict:
    subject = db.get_spine_subject(subject_id)
    if not subject:
        raise ValueError("Subject not found.")

    seeds = db.list_spine_seeds(subject_id)
    runs = db.list_spine_connector_runs(subject_id=subject_id)
    observations = db.list_spine_observations(subject_id)
    assertions = db.list_spine_assertions(subject_id)

    return {
        "subject": {
            "id": subject.id,
            "label": subject.label,
            "created_at": subject.created_at.isoformat()
            if subject.created_at
            else None,
        },
        "seeds": [
            {
                "id": seed.id,
                "type": seed.seed_type,
                "value": seed.normalized_value,
                "hash": seed.pii_hash,
            }
            for seed in seeds
        ],
        "summary": {
            "connector_runs": len(runs),
            "observations": len(observations),
            "assertions": len(assertions),
            "validated_assertions": len(
                [a for a in assertions if a.validation_state == "confirmed"]
            ),
        },
        "assertions": [
            {
                "id": item.id,
                "type": item.assertion_type,
                "value": item.normalized_value,
                "confidence": float(item.confidence or 0),
                "band": confidence_band(float(item.confidence or 0)),
                "validation_state": item.validation_state,
                "payload": json.loads(item.payload_json or "{}"),
            }
            for item in assertions
        ],
        "runs": [
            {
                "id": run.id,
                "connector": run.connector_key,
                "status": run.status,
                "created_at": run.created_at.isoformat()
                if run.created_at
                else None,
            }
            for run in runs
        ],
    }
