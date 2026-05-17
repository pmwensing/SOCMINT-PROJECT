#!/usr/bin/env bash
set -euo pipefail

ROOT="${SOCMINT_ROOT:-$(pwd)}"
cd "$ROOT"

docker compose exec -T app python - <<'PY2'
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from src.socmint import database as db
from src.socmint.command_center import command_center_payload
from src.socmint.entity_dossier_v2 import export_full_entity_dossier_v2
from src.socmint.full_report_history import full_report_export_history


def fail(message: str) -> None:
    raise SystemExit(f"FAIL v11.2 subject workflow smoke: {message}")


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


db.ensure_configured()

stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
label = f"v11.2-smoke-subject-{stamp}"
seed_raw = f"v11.2.test.{stamp}"
seed_norm = seed_raw.lower().strip()
seed_hash = hashlib.sha256(seed_norm.encode("utf-8")).hexdigest()

print("[+] Create subject")
subject_id = db.create_spine_subject(label=label)
require(isinstance(subject_id, int) and subject_id > 0, "subject id was not created")

subject = db.get_spine_subject(subject_id)
require(subject is not None, "created subject could not be reloaded")
require(subject.label == label, "created subject label mismatch")

print("[+] Add seed")
seed_id = db.add_spine_seed(
    subject_id=subject_id,
    seed_type="username",
    raw_value=seed_raw,
    normalized_value=seed_norm,
    pii_hash=seed_hash,
)
require(isinstance(seed_id, int) and seed_id > 0, "seed id was not created")

seeds = db.list_spine_seeds(subject_id)
require(any(item.id == seed_id for item in seeds), "created seed not listed")

print("[+] Create deterministic connector run")
raw_result = {
    "schema": "socmint.v11_2.functional_smoke.connector_result",
    "status": "completed",
    "connector": "v11_2_local_smoke",
    "seed": seed_norm,
    "findings": [
        {
            "source": "v11_2_local_smoke",
            "type": "username_profile",
            "value": seed_norm,
            "confidence": 0.91,
            "context": {
                "profile_url": f"https://example.test/{seed_norm}",
                "note": "deterministic local smoke result; no live external lookup performed",
            },
        }
    ],
}
run_id = db.create_spine_connector_run(
    subject_id=subject_id,
    connector_key="v11_2_local_smoke",
    seed_id=seed_id,
    status="completed",
    raw_result=raw_result,
)
require(isinstance(run_id, int) and run_id > 0, "connector run id was not created")

runs = db.list_spine_connector_runs(subject_id=subject_id)
require(any(item.id == run_id and item.status == "completed" for item in runs), "connector run not listed as completed")

print("[+] Register raw artifact")
artifact_root = Path("var/socmint/v11_2_smoke_artifacts")
artifact_root.mkdir(parents=True, exist_ok=True)
artifact_path = artifact_root / f"subject-{subject_id}-connector-result.json"
artifact_payload = {
    "subject_id": subject_id,
    "seed_id": seed_id,
    "run_id": run_id,
    "raw_result": raw_result,
}
artifact_path.write_text(json.dumps(artifact_payload, indent=2, sort_keys=True))
artifact_sha = hashlib.sha256(artifact_path.read_bytes()).hexdigest()

artifact_id = db.create_spine_raw_artifact(
    run_id=run_id,
    kind="connector_result_json",
    path=str(artifact_path),
    sha256=artifact_sha,
    mime_type="application/json",
    size_bytes=artifact_path.stat().st_size,
    meta={
        "schema": "socmint.v11_2.functional_smoke.artifact",
        "subject_id": subject_id,
        "seed_id": seed_id,
        "run_id": run_id,
    },
)
require(isinstance(artifact_id, int) and artifact_id > 0, "raw artifact id was not created")

artifacts = db.list_spine_raw_artifacts(run_id=run_id)
require(any(item.id == artifact_id and item.sha256 == artifact_sha for item in artifacts), "raw artifact not listed with expected hash")

print("[+] Create observation")
observation_payload = {
    "schema": "socmint.v11_2.functional_smoke.observation",
    "diagnostic": False,
    "connector": "v11_2_local_smoke",
    "seed": seed_norm,
    "profile_url": f"https://example.test/{seed_norm}",
    "evidence_artifact_id": artifact_id,
}
observation_id = db.create_spine_observation(
    subject_id=subject_id,
    run_id=run_id,
    observation_type="username_profile",
    normalized_value=seed_norm,
    confidence="0.91",
    source_ref="v11_2_local_smoke",
    evidence_ref=str(artifact_path),
    payload=observation_payload,
)
require(isinstance(observation_id, int) and observation_id > 0, "observation id was not created")

observations = db.list_spine_observations(subject_id)
require(any(item.id == observation_id for item in observations), "created observation not listed")

print("[+] Upsert and validate assertion")
assertion_payload = {
    "schema": "socmint.v11_2.functional_smoke.assertion",
    "source_observation_id": observation_id,
    "seed_id": seed_id,
    "run_id": run_id,
    "value": seed_norm,
}
assertion_id = db.upsert_spine_assertion(
    subject_id=subject_id,
    assertion_type="identity_handle",
    normalized_value=seed_norm,
    confidence="0.91",
    validation_state="unreviewed",
    payload=assertion_payload,
)
require(isinstance(assertion_id, int) and assertion_id > 0, "assertion id was not created")

validated_id = db.validate_spine_assertion(
    assertion_id=assertion_id,
    actor="v11.2-smoke",
    action="confirmed",
    note="v11.2 functional smoke confirmed deterministic local assertion",
)
require(validated_id == assertion_id, "assertion validation failed")

assertion = db.get_spine_assertion(assertion_id)
require(assertion is not None, "validated assertion not found")
require(assertion.validation_state == "confirmed", "assertion validation state is not confirmed")

print("[+] Upsert account discovery")
discovery = db.upsert_account_discovery(
    subject_id=subject_id,
    observation_id=observation_id,
    discovery_type="username_profile",
    account_value=seed_norm,
    platform="example.test",
    profile_url=f"https://example.test/{seed_norm}",
    confidence="0.91",
    assertion_id=assertion_id,
    capture_ids=[artifact_id],
    payload={
        "schema": "socmint.v11_2.functional_smoke.account_discovery",
        "run_id": run_id,
        "artifact_id": artifact_id,
    },
    actor="v11.2-smoke",
)
require(discovery is not None and discovery.id > 0, "account discovery was not created")

discoveries = db.list_account_discoveries(subject_id=subject_id)
require(any(item.id == discovery.id for item in discoveries), "account discovery not listed")

print("[+] Export full entity dossier v2")
export = export_full_entity_dossier_v2(subject_id)

required_export_keys = [
    "json_path",
    "markdown_path",
    "html_path",
    "manifest_path",
    "zip_path",
    "result_path",
    "dossier",
    "manifest",
]
for key in required_export_keys:
    require(export.get(key), f"export missing {key}")

for key in ["json_path", "markdown_path", "html_path", "manifest_path", "zip_path", "result_path"]:
    path = Path(export[key])
    require(path.exists(), f"export file missing: {key}={path}")
    require(path.stat().st_size > 0, f"export file empty: {key}={path}")

score = export["dossier"].get("score") or {}
require(score.get("real_observation_count", 0) >= 1, "dossier score missing real observation")
require(score.get("assertion_count", 0) >= 1, "dossier score missing assertion")

manifest = export.get("manifest") or {}
roles = {item.get("role") for item in manifest.get("files", [])}
for role in {"dossier_json", "dossier_markdown", "dossier_html", "export_manifest", "zip_bundle"}:
    require(role in roles, f"manifest missing role {role}")

print("[+] Verify full-report export history")
history = full_report_export_history(subject_id, limit=5)
require(history.get("count", 0) >= 1, "full report export history did not find export")

latest = (history.get("exports") or [None])[0] or {}
require(latest.get("artifact_count", 0) >= 4, "latest history artifact count too low")
require("zip_bundle" in set(latest.get("artifact_roles") or []), "latest history missing zip_bundle role")

print("[+] Verify command center sees subject/report")
cc = command_center_payload()
subjects = cc.get("subjects") or []
matching_subjects = [item for item in subjects if item.get("id") == subject_id]
require(matching_subjects, "command center payload does not include smoke subject")
require(matching_subjects[0].get("latest_report_available") is True, "command center did not detect latest report")
require((cc.get("summary") or {}).get("report_count", 0) >= 1, "command center summary report_count did not increase")

summary = {
    "schema": "socmint.v11_2.subject_workflow_functional_smoke",
    "status": "pass",
    "subject_id": subject_id,
    "label": label,
    "seed_id": seed_id,
    "run_id": run_id,
    "artifact_id": artifact_id,
    "observation_id": observation_id,
    "assertion_id": assertion_id,
    "discovery_id": discovery.id,
    "export": {
        "json": export["json_path"],
        "markdown": export["markdown_path"],
        "html": export["html_path"],
        "manifest": export["manifest_path"],
        "zip": export["zip_path"],
        "result": export["result_path"],
    },
    "score": score,
    "history_count": history.get("count"),
    "command_center_subject": matching_subjects[0],
}

print(json.dumps(summary, indent=2, sort_keys=True))
print("PASS subject workflow functional smoke v11.2")
PY2
