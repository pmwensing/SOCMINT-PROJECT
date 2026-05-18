#!/usr/bin/env bash
set -euo pipefail

echo "[+] v12.6 narrative intelligence smoke"
rm -rf var/test_v12_6 || true
mkdir -p var/test_v12_6

PYTHONPATH=src python3 - <<'PY'
import json
from pathlib import Path
from src.socmint.forensic_intake_v12_5 import ensure_dropzones, dropzones_root, ingest_dropzones
from src.socmint.narrative_intelligence_v12_6 import story_reconstruction_payload

root = "var/test_v12_6"
ensure_dropzones(root)
base = Path(dropzones_root(root))
(base / "documents" / "timeline_note.txt").write_text("On 2026-05-18 analyst@example.com confirmed preservation of evidence. Phone 613-555-0101 was mentioned.\n")
(base / "email_exports" / "thread.eml").write_text("From: analyst@example.com\nTo: subject@example.com\nSubject: Evidence timeline\n\nClaim: document preserved.\n")

report = ingest_dropzones(actor="test-v12-6", root=root)
assert report["ingested_count"] >= 2
payload = story_reconstruction_payload(root=root)
print(json.dumps(payload, indent=2))
assert payload["schema"] == "socmint.narrative_intelligence.v12_6"
assert payload["timeline"]["event_count"] >= 2
assert len(payload["claims"]) >= 2
assert "contradictions" in payload
assert "communication_graph" in payload
assert "narrative_confidence" in payload
assert "court_lawyer_ready_narrative" in payload
assert "dossier_auto_story_layer" in payload
print("PASS v12.6 narrative intelligence + story reconstruction smoke")
PY
