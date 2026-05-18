#!/usr/bin/env bash
set -euo pipefail

echo "[+] v12.3.2 recon dashboard UI smoke"
PYTHONPATH=src python3 - <<'PY'
import json
from src.socmint.recon_document_locator_routes import recon_document_locator_dashboard_payload

payload = recon_document_locator_dashboard_payload("example.com")
print(json.dumps(payload, indent=2))
assert payload["schema"] == "socmint.recon.document_locator_ui.v12_3_2"
assert payload["search"] is not None
assert len(payload["dork_templates"]) >= 6
assert len(payload["source_trust_matrix"]) >= 3
assert len(payload["legal_safety_matrix"]) >= 4
assert payload["v12_5_handoff"]["state"] == "manual_acquisition_queue"
print("PASS v12.3.2 recon dashboard UI smoke")
PY
