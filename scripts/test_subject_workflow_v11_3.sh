#!/usr/bin/env bash
set -euo pipefail

ROOT="${SOCMINT_ROOT:-$(pwd)}"
cd "$ROOT"

echo "[+] v11.3 pre-clean"
./scripts/clean_v11_smoke_data.sh

docker compose exec -T app python - <<'PY'
from __future__ import annotations

import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path

from src.socmint import database as db
from src.socmint.command_center import command_center_payload
from src.socmint.entity_dossier_v2 import export_full_entity_dossier_v2
from src.socmint.full_report_history import full_report_export_history

PREFIX = "v11-smoke-"


def fail(message: str) -> None:
    raise SystemExit(f"FAIL v11.3 subject workflow smoke: {message}")


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def verify_export(subject_id: int) -> dict:
    export = export_full_entity_dossier_v2(subject_id)
    for key in ["json_path", "markdown_path", "html_path", "manifest_path", "zip_path", "result_path", "dossier", "manifest"]:
        require(export.get(key), f"export missing {key}")
    for key in ["json_path", "markdown_path", "html_path", "manifest_path", "zip_path", "result_path"]:
        path = Path(export[key])
        require(path.exists(), f"export file missing: {path}")
        require(path.stat().st_size > 0, f"export file empty: {path}")
    score = export["dossier"].get("score") or {}
    require(score.get("real_observation_count", 0) >= 1, "dossier missing real observation")
    require(score.get("assertion_count", 0) >= 1, "dossier missing assertion")
    roles = {item.get("role") for item in (export.get("manifest") or {}).get("files", [])}
    for role in {"dossier_json", "dossier_markdown", "dossier_html", "export_manifest", "zip_bundle"}:
        require(role in roles, f"manifest missing {role}")
    return export


db.ensure_configured()
stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
label = f"{PREFIX}subject-{stamp}"
seed_raw = f"{PREFIX}test.{stamp}"
seed_norm = seed_raw.lower().strip()
seed_hash = hashlib.sha256(seed_norm.encode()).hexdigest()

print("[+] Create stable namespace subject")
subject_id = db.create_spine_subject(label=label)
require(subject_id > 0, "subject id not created")
subject = db.get_spine_subject(subject_id)
require(subject and subject.label == label, "subject reload failed")
require(subject.label.startswith(PREFIX), "subject missing smoke namespace")

print("[+] Add seed")
seed_id = db.add_spine_seed(subject_id, "username", seed_raw, seed_norm, seed_hash)
require(seed_id > 0, "seed not created")

print("[+] Create connector run and tagged artifact")
raw_result = {
    "schema": "socmint.v11_3.functional_smoke.connector_result",
    "status": "completed",
    "connector": "v11_3_local_smoke",
    "seed": seed_norm,
    "test_data": True,
    "cleanup_namespace": PREFIX,
    "findings": [{"source": "v11_3_local_smoke", "type": "username_profile", "value": seed_norm, "confidence": 0.93}],
}
run_id = db.create_spine_connector_run(subject_id, "v11_3_local_smoke", seed_id, "completed", raw_result)
require(run_id > 0, "run not created")

artifact_root = Path("var/socmint/v11_3_smoke_artifacts")
artifact_root.mkdir(parents=True, exist_ok=True)
artifact_path = artifact_root / f"subject-{subject_id}-connector-result.json"
artifact_path.write_text(json.dumps({"test_data": True, "cleanup_namespace": PREFIX, "raw_result": raw_result}, indent=2))
artifact_sha = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
artifact_id = db.create_spine_raw_artifact(run_id, "connector_result_json", str(artifact_path), artifact_sha, "application/json", artifact_path.stat().st_size, {"test_data": True, "cleanup_namespace": PREFIX})
require(artifact_id > 0, "artifact not created")

print("[+] Create observation/assertion/account discovery")
observation_id = db.create_spine_observation(subject_id, run_id, "username_profile", seed_norm, "0.93", "v11_3_local_smoke", str(artifact_path), {"test_data": True, "cleanup_namespace": PREFIX, "diagnostic": False})
require(observation_id > 0, "observation not created")
assertion_id = db.upsert_spine_assertion(subject_id, "identity_handle", seed_norm, "0.93", "unreviewed", {"test_data": True, "cleanup_namespace": PREFIX, "source_observation_id": observation_id})
require(assertion_id > 0, "assertion not created")
require(db.validate_spine_assertion(assertion_id, "v11.3-smoke", "confirmed", "v11.3 smoke confirmed") == assertion_id, "assertion validation failed")
discovery = db.upsert_account_discovery(subject_id, observation_id, "username_profile", seed_norm, platform="example.test", profile_url=f"https://example.test/{seed_norm}", confidence="0.93", assertion_id=assertion_id, capture_ids=[artifact_id], payload={"test_data": True, "cleanup_namespace": PREFIX}, actor="v11.3-smoke")
require(discovery and discovery.id > 0, "discovery not created")

print("[+] Export twice and verify re-run-safe history")
first = verify_export(subject_id)
# export_full_entity_dossier_v2 currently uses second-level timestamps in filenames.
# Sleep across the boundary so this smoke verifies repeated export history rather than
# failing due to same-second filename collision/overwrite.
time.sleep(1.2)
second = verify_export(subject_id)
require(first["zip_path"] != second["zip_path"], "exports collided on zip_path")
require(first["result_path"] != second["result_path"], "exports collided on result_path")
history = full_report_export_history(subject_id, limit=10)
exports = history.get("exports") or []
require(history.get("count", 0) >= 2, f"history missing repeated exports: count={history.get('count')} exports={len(exports)}")
zip_names = [item.get("zip_name") for item in exports if item.get("zip_name")]
require(len(set(zip_names)) >= 2, "history zip names are not unique")
require("zip_bundle" in set((exports[0] or {}).get("artifact_roles") or []), "latest history missing zip bundle")

print("[+] Verify Command Center sees test subject/report")
cc = command_center_payload()
subjects = cc.get("subjects") or []
match = [item for item in subjects if item.get("id") == subject_id]
require(match, "command center missing smoke subject")
require(match[0].get("latest_report_available") is True, "command center missing latest report flag")
require(match[0].get("label", "").startswith(PREFIX), "command center subject missing smoke namespace")

print(json.dumps({
    "schema": "socmint.v11_3.subject_workflow_rerun_stability",
    "status": "pass",
    "cleanup_namespace": PREFIX,
    "subject_id": subject_id,
    "label": label,
    "seed_id": seed_id,
    "run_id": run_id,
    "artifact_id": artifact_id,
    "observation_id": observation_id,
    "assertion_id": assertion_id,
    "discovery_id": discovery.id,
    "exports": [first["zip_path"], second["zip_path"]],
    "history_count": history.get("count"),
    "command_center_subject": match[0],
}, indent=2, sort_keys=True))
print("PASS subject workflow re-run stability smoke v11.3")
PY

echo "[+] v11.3 post-clean"
./scripts/clean_v11_smoke_data.sh

echo "PASS v11.3 test data hygiene and re-run stability"
