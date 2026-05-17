#!/usr/bin/env bash
set -euo pipefail

ROOT="${SOCMINT_ROOT:-$(pwd)}"
cd "$ROOT"

bash ./scripts/clean_v11_smoke_data.sh

echo "[+] v11.9 direct payload and promotion smoke"
docker compose exec -T app python - <<'PY'
import hashlib
import json
from src.socmint import database as db
from src.socmint.artifacts import write_json_artifact
from src.socmint.spine_intelligence_v11_9 import spine_intelligence_payload, promote_observation_to_assertion

db.ensure_configured()
subject_id = db.create_spine_subject(label="v11-smoke-real-enrichment-ux")
seed = "v11_smoke_user"
seed_id = db.add_spine_seed(
    subject_id=subject_id,
    seed_type="username",
    raw_value=seed,
    normalized_value=seed,
    pii_hash=hashlib.sha256(seed.encode()).hexdigest(),
)
raw_result = {
    "connector": "sherlock",
    "seed_type": "username",
    "seed_hash": "smoke",
    "result": {
        "connector": "sherlock",
        "target": seed,
        "target_type": "username",
        "status": "completed",
        "returncode": 0,
        "stdout": "[+] GitHub: https://github.com/v11_smoke_user\n",
        "stderr": "",
    },
}
artifact = write_json_artifact("connector-runs", raw_result, prefix=f"v11-9-{subject_id}")
run_id = db.create_spine_connector_run(subject_id, "sherlock", seed_id, "completed", raw_result)
db.create_spine_raw_artifact(
    run_id=run_id,
    kind=artifact["kind"],
    path=artifact["path"],
    sha256=artifact["sha256"],
    mime_type=artifact["mime_type"],
    size_bytes=artifact["size_bytes"],
    meta=raw_result,
)
observation_id = db.create_spine_observation(
    subject_id=subject_id,
    run_id=run_id,
    observation_type="profile_url",
    normalized_value="https://github.com/v11_smoke_user",
    confidence="0.82",
    source_ref=f"run:{run_id}:sherlock",
    evidence_ref=f"sha256:{artifact['sha256']}",
    payload={
        "type": "profile_url",
        "value": "https://github.com/v11_smoke_user",
        "connector": "sherlock",
        "diagnostic": False,
        "normalizer_schema": "socmint.connector_normalizers.v11_9",
    },
)
payload = spine_intelligence_payload(subject_id)
print(json.dumps({
    "schema": payload["schema"],
    "summary": payload["summary"],
    "run_badge": payload["runs"][0]["badge"],
}, indent=2, sort_keys=True))
assert payload["schema"] == "socmint.spine_intelligence.v11_9"
assert payload["summary"]["real_run_count"] >= 1
assert payload["summary"]["dossier_readiness_gate"]["status"] == "hold"
assert payload["runs"][0]["badge"] == "real"
assert payload["runs"][0]["normalized_findings"]
assert payload["runs"][0]["observations"]

promoted = promote_observation_to_assertion(observation_id, actor="v11.9-smoke", note="promotion smoke")
assert promoted["assertion_id"]
post = spine_intelligence_payload(subject_id)
assert post["summary"]["confirmed_assertions"] >= 1
assert post["summary"]["dossier_readiness_gate"]["status"] == "pass"
print("PASS v11.9 direct run inspector/promotion/readiness smoke")
PY

echo "[+] v11.9 browser/API smoke"
docker compose exec -T app python - <<'PY'
from src.socmint import database as db
from src.socmint.wsgi import app

subject = db.list_spine_subjects(limit=1)[0]
client = app.test_client()
with client.session_transaction() as sess:
    sess["user"] = "v11.9-smoke"
    sess["is_admin"] = True
    sess["role"] = "admin"

api = client.get(f"/api/v1/spine/subjects/{subject.id}/intelligence")
assert api.status_code == 200, api.status_code
payload = api.get_json()
assert payload["schema"] == "socmint.spine_intelligence.v11_9"
assert payload["summary"]["dossier_readiness_gate"]["status"] in {"pass", "hold"}

page = client.get(f"/spine/subjects/{subject.id}/intelligence")
assert page.status_code == 200, page.status_code
html = page.get_data(as_text=True)
assert "Connector Run Result Inspector" in html
assert "Dossier Readiness Gate" in html
assert "Promotion-ready observations" in html or "Dossier Assertions" in html
print("PASS v11.9 browser/API smoke")
PY

echo "PASS v11.9 real enrichment run UX and evidence promotion smoke"
