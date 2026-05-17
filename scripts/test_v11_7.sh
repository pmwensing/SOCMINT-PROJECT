#!/usr/bin/env bash
set -euo pipefail

ROOT="${SOCMINT_ROOT:-$(pwd)}"
cd "$ROOT"

echo "[+] Connector runtime health payload"
docker compose exec -T app python - <<'PY'
import json
from src.socmint.connector_runtime import connector_runtime_health

payload = connector_runtime_health()
print(json.dumps(payload["summary"], indent=2, sort_keys=True))
ready = {item["name"] for item in payload["connectors"] if item["status"] == "ready"}
expected = {"maigret", "sherlock", "socialscan", "holehe", "h8mail"}
missing = sorted(expected - ready)
if missing:
    raise SystemExit(f"FAIL connector CLIs not ready in Docker image: {missing}. Rebuild with --build-arg SOCMINT_INSTALL_CONNECTORS=true")
for optional in {"phoneinfoga", "archivebox"}:
    assert optional in {item["name"] for item in payload["connectors"]}
print("PASS connector runtime ready set", sorted(ready))
PY

echo "[+] Template render smoke via Flask test client"
docker compose exec -T app python - <<'PY'
from src.socmint.wsgi import app

client = app.test_client()
with client.session_transaction() as sess:
    sess["user"] = "v11.7-smoke"
    sess["is_admin"] = True
    sess["role"] = "admin"

page = client.get("/connectors/runtime")
assert page.status_code == 200, page.status_code
html = page.get_data(as_text=True)
assert "Connector Runtime" in html
assert "Connector Health" in html
assert "builtin_function_or_method" not in html
api = client.get("/api/v1/connectors/runtime")
assert api.status_code == 200, api.status_code
assert api.json["schema"] == "socmint.connector_runtime.v7_6_1"
print("PASS /connectors/runtime page/API smoke")
PY

echo "PASS v11.7 connector runtime Docker toolchain smoke"
