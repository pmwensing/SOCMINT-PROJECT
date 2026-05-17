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
ADMIN_USER="${SOCMINT_TEST_ADMIN_USER:-$(grep '^SOCMINT_ADMIN_USER=' .env | cut -d= -f2-)}"
ADMIN_PASS="${SOCMINT_TEST_ADMIN_PASSWORD:-$(grep '^SOCMINT_ADMIN_PASSWORD=' .env | cut -d= -f2-)}"

docker compose exec -T \
  -e ADMIN_USER="$ADMIN_USER" \
  -e ADMIN_PASS="$ADMIN_PASS" \
  app python - <<'PY'
import json
import os
import re
import urllib.parse
import urllib.request
import http.cookiejar

base = "http://127.0.0.1:5000"
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(cj),
    urllib.request.HTTPRedirectHandler(),
)
login_html = opener.open(base + "/login", timeout=5).read().decode(errors="ignore")
m = re.search(r'name=["\']csrf_token["\'][^>]*value=["\']([^"\']+)["\']', login_html)
if not m:
    m = re.search(r'value=["\']([^"\']+)["\'][^>]*name=["\']csrf_token["\']', login_html)
if not m:
    raise SystemExit("FAIL csrf token not found")
csrf = m.group(1)
data = urllib.parse.urlencode({
    "username": os.environ["ADMIN_USER"],
    "password": os.environ["ADMIN_PASS"],
    "csrf_token": csrf,
}).encode()
opener.open(
    urllib.request.Request(base + "/login", data=data, headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST"),
    timeout=5,
).read()

response = opener.open(base + "/api/v1/admin/runtime/import-health", timeout=5)
body = response.read().decode()
print(body)
payload = json.loads(body)
if response.status != 200:
    raise SystemExit("FAIL import-health did not return 200")
if payload.get("schema") != "socmint.runtime_import_health.v11_5":
    raise SystemExit("FAIL import-health schema mismatch")
if payload.get("status") != "pass":
    raise SystemExit("FAIL import-health status is not pass")

cc = json.loads(opener.open(base + "/api/v1/command-center", timeout=5).read().decode())
if "runtime_import_health" not in cc:
    raise SystemExit("FAIL command center missing runtime_import_health")
if cc["runtime_import_health"]["status"] != "pass":
    raise SystemExit("FAIL command center runtime import health not pass")
print("PASS runtime import health API and command center payload")
PY

echo "PASS Docker runtime import stability smoke v11.5"
