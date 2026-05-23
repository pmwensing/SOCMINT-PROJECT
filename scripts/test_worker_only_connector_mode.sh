#!/usr/bin/env bash
set -euo pipefail

echo "[+] Worker-only connector mode smoke"
PYTHONPATH=src python3 - <<'PY'
import os
from src.socmint.connectors import connector_mode_report, run_connector

os.environ["SOCMINT_CONNECTOR_MODE"] = "real"
os.environ["SOCMINT_AUTHORIZED_REALWORLD_CONNECTORS"] = "true"
os.environ.pop("SOCMINT_WORKER_PROCESS", None)
os.environ.pop("SOCMINT_ALLOW_WEB_REAL_CONNECTORS", None)
web = connector_mode_report()
print(web)
assert web["requested_mode"] == "real"
assert web["effective_mode"] == "diagnostic"
assert web["real_world_enabled"] is False
payload = run_connector("holehe", "authorized@example.com", "email")
assert payload["status"] == "dry_run"
assert payload["execution_mode"] == "diagnostic"

os.environ["SOCMINT_WORKER_PROCESS"] = "true"
worker = connector_mode_report()
print(worker)
assert worker["effective_mode"] == "real"
assert worker["real_world_enabled"] is True

os.environ["SOCMINT_WORKER_PROCESS"] = "false"
os.environ["SOCMINT_ALLOW_WEB_REAL_CONNECTORS"] = "true"
allowed_web = connector_mode_report()
print(allowed_web)
assert allowed_web["effective_mode"] == "real"
print("PASS worker-only connector mode smoke")
PY
