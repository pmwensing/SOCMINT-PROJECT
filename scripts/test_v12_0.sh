#!/usr/bin/env bash
set -euo pipefail

echo "[+] v12.0 route audit"
bash ./scripts/test_frontend_routes_v11.sh

echo "[+] v11.9 chain"
make test-v11-9

echo "[+] connector runtime readiness"
PYTHONPATH=src python3 -m socmint.connector_runtime_health_cli --json

echo "[+] full dossier production gate smoke"
PYTHONPATH=src python3 - <<'PY'
import json
from src.socmint.production_gate_v12 import production_release_gate

subject_id = 1
report = production_release_gate(subject_id)
print(json.dumps(report, indent=2))
assert report["schema"] == "socmint.production_gate.v12_0"
assert report["release_gate_decision"] in {"GO", "HOLD", "FAIL"}
print("PASS v12.0 production release gate smoke")
PY
