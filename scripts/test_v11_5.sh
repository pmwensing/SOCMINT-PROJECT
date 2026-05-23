#!/usr/bin/env bash
set -euo pipefail

ROOT="${SOCMINT_ROOT:-$(pwd)}"
cd "$ROOT"

echo "[+] Source scan for legacy absolute imports"
if grep -RInE '^\s*(import|from)\s+socmint\b' src/socmint --include='*.py'; then
  echo "FAIL legacy absolute socmint imports remain"
  exit 1
fi

echo "[+] Runtime import health direct"
docker compose exec -T app python - <<'PY'
import json
from src.socmint.runtime_import_health import runtime_import_health_report
report = runtime_import_health_report()
print(json.dumps(report, indent=2, sort_keys=True))
if report["status"] != "pass":
    raise SystemExit("FAIL runtime import health is not pass")
print("PASS runtime import health direct")
PY

echo "[+] Docker boot log smoke"
docker compose logs --tail=400 app > /tmp/socmint-v11-5-app.log
if grep -q "No module named 'socmint'" /tmp/socmint-v11-5-app.log; then
  echo "FAIL Docker app logs still contain: No module named 'socmint'"
  cat /tmp/socmint-v11-5-app.log
  exit 1
fi

echo "[+] Authenticated route smoke for import-health"
docker compose exec -T app python - <<'PY'
import json
from src.socmint.wsgi import app

client = app.test_client()
with client.session_transaction() as sess:
    sess["user"] = "v11.5-import-health-smoke"
    sess["is_admin"] = True
    sess["role"] = "admin"

response = client.get("/api/v1/admin/runtime/import-health")
body = response.get_data(as_text=True)
print(body)
if response.status_code != 200:
    raise SystemExit(f"FAIL import-health did not return 200: {response.status_code}")
payload = json.loads(body)
if payload.get("schema") != "socmint.runtime_import_health.v11_5":
    raise SystemExit("FAIL import-health schema mismatch")
if payload.get("status") != "pass":
    raise SystemExit("FAIL import-health status is not pass")

cc_response = client.get("/api/v1/command-center")
if cc_response.status_code != 200:
    raise SystemExit(f"FAIL command-center did not return 200: {cc_response.status_code}")
cc = cc_response.get_json()
if "runtime_import_health" not in cc:
    raise SystemExit("FAIL command center missing runtime_import_health")
if cc["runtime_import_health"]["status"] != "pass":
    raise SystemExit("FAIL command center runtime import health not pass")
print("PASS runtime import health API and command center payload")
PY

echo "PASS Docker runtime import stability smoke v11.5"
