#!/usr/bin/env bash
set -euo pipefail

echo "[+] social-analyzer deep profile enrichment connector smoke"
PYTHONPATH=src python3 - <<'PY'
import json
import os
from src.socmint.connector_normalizers import normalize_connector_output
from src.socmint.social_analyzer_connector_v12_10_2 import command_for_target, run_social_analyzer
from src.socmint.spine import HIGH_VALUE_CONNECTORS, extract_observations

class Seed:
    id = 1
    seed_type = "username"
    normalized_value = "authorizedtest"
    pii_hash = "hash-authorizedtest"

artifact = {"sha256": "0" * 64}

assert "social-analyzer" in HIGH_VALUE_CONNECTORS
assert HIGH_VALUE_CONNECTORS["social-analyzer"].get("deep_enrichment") is True
assert HIGH_VALUE_CONNECTORS["social-analyzer"]["base"] >= 0.7
assert "socialscan" in HIGH_VALUE_CONNECTORS

cmd = command_for_target("authorizedtest@example.com", "email")
print(json.dumps({"command": cmd}, indent=2))
assert cmd[0] == "social-analyzer"
assert "authorizedtest" in cmd
assert "--output" in cmd and "json" in cmd

raw = {
    "status": "completed",
    "stdout": json.dumps([
        {"site": "GitHub", "status": "found", "url": "https://github.com/authorizedtest", "score": 92},
        {"platform": "ExampleNet", "found": True, "profile_url": "https://example.net/authorizedtest", "rating": 81},
    ]),
    "stderr": "",
    "findings": [],
}
findings = normalize_connector_output("social-analyzer", "authorizedtest", "username", raw)
print(json.dumps({"findings": findings}, indent=2))
assert any(item["type"] == "profile_url" for item in findings)
assert all(item.get("context", {}).get("deep_enrichment") for item in findings if item["type"] in {"profile_url", "platform_presence"})

observations = extract_observations("social-analyzer", Seed(), raw, HIGH_VALUE_CONNECTORS["social-analyzer"], artifact)
print(json.dumps({"observations": observations}, indent=2))
assert observations
assert any(item.get("deep_enrichment") for item in observations)
assert any(item["type"] == "profile_url" for item in observations)

os.environ["SOCMINT_CONNECTOR_MODE"] = "diagnostic"
os.environ.pop("SOCMINT_AUTHORIZED_REALWORLD_CONNECTORS", None)
os.environ.pop("SOCMINT_WORKER_PROCESS", None)
dry = run_social_analyzer("authorizedtest", "username")
print(json.dumps({"dry_status": dry["status"], "mode": dry["execution_mode"]}, indent=2))
assert dry["status"] == "dry_run"
assert dry["execution_mode"] == "diagnostic"

print("PASS social-analyzer connector smoke")
PY
