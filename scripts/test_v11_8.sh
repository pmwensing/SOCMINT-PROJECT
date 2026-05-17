#!/usr/bin/env bash
set -euo pipefail

ROOT="${SOCMINT_ROOT:-$(pwd)}"
cd "$ROOT"

echo "[+] Connector run QA direct report"
docker compose exec -T app python - <<'PY'
import json
from src.socmint.connector_run_qa import connector_run_qa_report

report = connector_run_qa_report()
print(json.dumps({
    "schema": report["schema"],
    "status": report["status"],
    "normalization_status": report["normalization"]["status"],
    "runtime_status": report["runtime"]["status"],
    "qa_gate": report["qa_gate"],
}, indent=2, sort_keys=True))
assert report["schema"] == "socmint.connector_run_qa.v11_8"
assert report["normalization"]["status"] == "pass"
assert report["runtime"]["status"] == "pass"
assert report["qa_gate"]["decision"] == "go"
print("PASS connector run QA direct report")
PY

echo "[+] Connector run QA API smoke"
docker compose exec -T app python - <<'PY'
from src.socmint.wsgi import app

client = app.test_client()
with client.session_transaction() as sess:
    sess["user"] = "v11.8-smoke"
    sess["is_admin"] = True
    sess["role"] = "admin"

response = client.get("/api/v1/admin/connectors/run-qa")
assert response.status_code == 200, response.status_code
payload = response.get_json()
assert payload["schema"] == "socmint.connector_run_qa.v11_8"
assert payload["normalization"]["status"] == "pass"
assert payload["runtime"]["status"] == "pass"
assert payload["qa_gate"]["decision"] == "go"
print("PASS /api/v1/admin/connectors/run-qa smoke")
PY

echo "PASS v11.8 real connector run QA and normalization smoke"
