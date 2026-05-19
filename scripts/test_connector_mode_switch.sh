#!/usr/bin/env bash
set -euo pipefail

echo "[+] Connector mode switch smoke"
PYTHONPATH=src python3 - <<'PY'
import os
from src.socmint.connectors import connector_mode_report, run_connector

# Default safety mode must not execute live connectors.
os.environ.pop("SOCMINT_CONNECTOR_MODE", None)
os.environ.pop("SOCMINT_AUTHORIZED_REALWORLD_CONNECTORS", None)
os.environ.pop("SOCMINT_WORKER_PROCESS", None)
os.environ.pop("SOCMINT_ALLOW_WEB_REAL_CONNECTORS", None)
report = connector_mode_report()
print(report)
assert report["effective_mode"] == "diagnostic"
payload = run_connector("holehe", "authorized@example.com", "email")
assert payload["status"] == "dry_run"
assert payload["execution_mode"] == "diagnostic"

# Dry-run mode remains non-live.
os.environ["SOCMINT_CONNECTOR_MODE"] = "dry-run"
os.environ.pop("SOCMINT_AUTHORIZED_REALWORLD_CONNECTORS", None)
os.environ.pop("SOCMINT_WORKER_PROCESS", None)
os.environ.pop("SOCMINT_ALLOW_WEB_REAL_CONNECTORS", None)
report = connector_mode_report()
print(report)
assert report["effective_mode"] == "dry-run"
payload = run_connector("holehe", "authorized@example.com", "email")
assert payload["status"] == "dry_run"
assert payload["execution_mode"] == "dry-run"

# Real requested without authorization falls back to diagnostic.
os.environ["SOCMINT_CONNECTOR_MODE"] = "real"
os.environ.pop("SOCMINT_AUTHORIZED_REALWORLD_CONNECTORS", None)
os.environ.pop("SOCMINT_WORKER_PROCESS", None)
os.environ.pop("SOCMINT_ALLOW_WEB_REAL_CONNECTORS", None)
report = connector_mode_report()
print(report)
assert report["requested_mode"] == "real"
assert report["effective_mode"] == "diagnostic"

# Real authorized in a web process still falls back to diagnostic by default.
os.environ["SOCMINT_CONNECTOR_MODE"] = "real"
os.environ["SOCMINT_AUTHORIZED_REALWORLD_CONNECTORS"] = "true"
os.environ.pop("SOCMINT_WORKER_PROCESS", None)
os.environ.pop("SOCMINT_ALLOW_WEB_REAL_CONNECTORS", None)
report = connector_mode_report()
print(report)
assert report["requested_mode"] == "real"
assert report["effective_mode"] == "diagnostic"
assert report["real_world_enabled"] is False

# Real authorized worker context enables live mode.
os.environ["SOCMINT_WORKER_PROCESS"] = "true"
report = connector_mode_report()
print(report)
assert report["effective_mode"] == "real"
assert report["real_world_enabled"] is True

# Explicit web override also enables live mode for emergency/manual testing.
os.environ["SOCMINT_WORKER_PROCESS"] = "false"
os.environ["SOCMINT_ALLOW_WEB_REAL_CONNECTORS"] = "true"
report = connector_mode_report()
print(report)
assert report["effective_mode"] == "real"
assert report["real_world_enabled"] is True
print("PASS connector mode switch smoke")
PY
