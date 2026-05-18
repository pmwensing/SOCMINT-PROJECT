#!/usr/bin/env bash
set -euo pipefail

echo "[+] v12.5 forensic intake smoke"
rm -rf var/test_v12_5 || true
mkdir -p var/test_v12_5

PYTHONPATH=src python3 - <<'PY'
import json
from pathlib import Path
from src.socmint.forensic_intake_v12_5 import ensure_dropzones, dropzones_root, ingest_dropzones, intake_dashboard_payload

root = "var/test_v12_5"
setup = ensure_dropzones(root)
print(json.dumps(setup, indent=2))

# Seed representative evidence
base = Path(dropzones_root(root))
(base / "documents" / "sample.txt").write_text("Test document evidence for forensic intake.\n")
(base / "images" / "sample.jpg").write_bytes(b"\xff\xd8\xff\xd9")
(base / "audio" / "sample.wav").write_bytes(b"RIFFTESTWAVE")
(base / "chat_exports" / "chat.json").write_text('{"messages": []}')

report = ingest_dropzones(actor="test-v12-5", root=root)
print(json.dumps(report, indent=2))
assert report["schema"] == "socmint.forensic_intake.v12_5"
assert report["ingested_count"] >= 4
assert report["manifest"]["schema"] == "socmint.forensic_preservation_manifest.v12_5"
assert report["manifest"]["court_safe_summary"]["hash_verified"] >= 4

ui = intake_dashboard_payload(root=root)
print(json.dumps(ui, indent=2))
assert ui["schema"] == "socmint.forensic_intake.v12_5"
assert len(ui["court_safe_rules"]) >= 4

print("PASS v12.5 forensic intake + drop-folder preservation smoke")
PY
