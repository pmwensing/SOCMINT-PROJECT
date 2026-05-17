#!/usr/bin/env bash
set -euo pipefail

ROOT="${SOCMINT_ROOT:-$(pwd)}"
cd "$ROOT"

./scripts/clean_v11_smoke_data.sh

echo "[+] Direct v11 readiness summary"
docker compose exec -T app python - <<'PY'
import json
from src.socmint.command_center import command_center_payload
from src.socmint.v11_readiness import v11_readiness_summary

summary = v11_readiness_summary()
print(json.dumps(summary, indent=2, sort_keys=True))
assert summary["schema"] == "socmint.v11_readiness.v11_6"
assert summary["baseline"] == "v11.6"
assert summary["total_checks"] == 6
names = {item["name"] for item in summary["checks"]}
for name in {"frontend_route_audit", "subject_workflow_smoke", "test_data_hygiene", "runtime_import_health", "tor_status", "worker_status"}:
    assert name in names, name
assert summary["release_gate"]["schema"] == "socmint.v11_release_gate.v11_6"
assert summary["status"] in {"pass", "needs_review"}

payload = command_center_payload()
assert payload["schema"] == "socmint.command_center.v11_6"
assert "v11_readiness" in payload
assert payload["summary"]["v11_readiness_status"] in {"pass", "needs_review"}
print("PASS v11.6 readiness direct payload")
PY

echo "[+] Authenticated route/page smoke"
python3 scripts/test_frontend_routes_v11.sh | tee /tmp/socmint-v11-6-frontend.log
grep -q '/api/v1/admin/v11/readiness-summary' /tmp/socmint-v11-6-frontend.log

docker compose exec -T app python - <<'PY'
import json
import urllib.request

# Route is login-protected in normal browser use. This direct internal import verifies the payload shape,
# while the frontend route audit verifies the authenticated route returns 200.
from src.socmint.v11_readiness import v11_readiness_summary
payload = v11_readiness_summary()
assert payload["schema"] == "socmint.v11_readiness.v11_6"
assert "release_gate" in payload
print(json.dumps({
    "schema": "socmint.v11_6.operator_readiness_smoke",
    "status": "pass",
    "readiness_status": payload["status"],
    "release_gate_decision": payload["release_gate"]["decision"],
    "passed_checks": payload["passed_checks"],
    "total_checks": payload["total_checks"],
}, indent=2, sort_keys=True))
PY

echo "PASS v11.6 operator readiness release gate smoke"
