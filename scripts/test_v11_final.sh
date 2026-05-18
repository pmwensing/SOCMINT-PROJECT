#!/usr/bin/env bash
set -euo pipefail

echo "[+] Full v11 chain"
make test-v11-9

echo "[+] v11.10 final handoff payload"
PYTHONPATH=src python3 - <<'PY'
import json
from src.socmint.v11_final_handoff import final_handoff_payload, write_final_handoff

report = final_handoff_payload()
print(json.dumps(report, indent=2))
assert report["schema"] == "socmint.v11_10.final_stabilization_handoff"
assert report["baseline"] == "v11 FINAL BASELINE"
assert report["release_gate_decision"] == "GO_FOR_V12_HANDOFF"
assert len(report["milestones"]) >= 11
assert report["v12_handoff"]["next_sequence"] == ["v12.0 RC", "v12.3 Recon Expansion", "v12.5 Forensic Intake"]
written = write_final_handoff()
assert written["json_path"].endswith("V11_10_FINAL_STABILIZATION_HANDOFF.json")
assert written["markdown_path"].endswith("V11_10_FINAL_STABILIZATION_HANDOFF.md")
print("PASS v11.10 final stabilization and RC handoff smoke")
PY
