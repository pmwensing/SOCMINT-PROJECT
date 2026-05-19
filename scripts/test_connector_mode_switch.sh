#!/usr/bin/env bash
set -euo pipefail

echo "[+] Connector mode switch smoke"
PYTHONPATH=src python3 - <<'PY'
import os
from src.socmint.connectors import connector_mode_report, run_connector

# Default safety mode must not execute live connectors.
os.environ.pop("SOCMINT_CONNECTOR_MODE", None)
os.environ.pop("SOCMINT_AUTHORIZED_REALWORLD_CONNECTORS", None)
report = connector_mode_report()
print(report)
assert report["effective_mode"] == "diagnostic"
payload = run_connector("holehe", "authorized@example.com", "email")
assert payload["status"] == "dry_run"
assert payload["execution_mode"] == "diagnostic"

# Dry-run mode remains non-live.
os.environ["SOCMINT_CONNECTOR_MODE"] = "dry-run"
os.environ.pop("SOCMINT_AUTHORIZED_REALWORLD_CONNECTORS", None)
report = connector_mode_report()
print(report)
assert report["effective_mode"] == "dry-run"
payload = run_connector("holehe", "authorized@example.com", "email")
assert payload["status"] == "dry_run"
assert payload["execution_mode"] == "dry-run"

# Real requested without authorization falls back to diagnostic.
os.environ["SOCMINT_CONNECTOR_MODE"] = "real"
os.environ.pop("SOCMINT_AUTHORIZED_REALWORLD_CONNECTORS", None)
report = connector_mode_report()
print(report)
assert report["requested_mode"] == "real"
assert report["effective_mode"] == "diagnostic"

# Real authorized enables real mode. This smoke does not call a connector in real mode.
os.environ["SOCMINT_CONNECTOR_MODE"] = "real"
os.environ["SOCMINT_AUTHORIZED_REALWORLD_CONNECTORS"] = "true"
report = connector_mode_report()
print(report)
assert report["effective_mode"] == "real"
assert report["real_world_enabled"] is True
print("PASS connector mode switch smoke")
PY
