#!/usr/bin/env bash
set -euo pipefail

echo "[+] v12.5.1 forensic dashboard UI smoke"
PYTHONPATH=src python3 - <<'PY'
import json
from src.socmint.forensic_intake_routes_v12_5_1 import forensic_dashboard_payload

payload = forensic_dashboard_payload()
print(json.dumps(payload, indent=2))
assert payload["schema"] == "socmint.forensic_intake_ui.v12_5_1"
assert "dropzone_browser" in payload
assert "vault_items" in payload
assert "manifest_index" in payload
assert "promotion_controls" in payload
assert "dossier_linkage" in payload
print("PASS v12.5.1 intake dashboard + evidence vault browser smoke")
PY
