#!/usr/bin/env bash
set -euo pipefail

echo "[+] v12.6.1 narrative polish + dossier story export smoke"
rm -rf var/test_v12_6_1 || true
mkdir -p var/test_v12_6_1

PYTHONPATH=src python3 - <<'PY'
import json
from pathlib import Path
from src.socmint.forensic_intake_v12_5 import ensure_dropzones, dropzones_root, ingest_dropzones
from src.socmint.narrative_export_v12_6_1 import narrative_dashboard_polish_payload, write_story_exports, dossier_story_layer

root = "var/test_v12_6_1"
ensure_dropzones(root)
base = Path(dropzones_root(root))
(base / "documents" / "story_note.txt").write_text("Narrative event: analyst@example.com confirmed preservation. Phone 613-555-0101 was mentioned.\n")
(base / "documents" / "claim_note.txt").write_text("Claim validation sample for dossier story layer.\n")
report = ingest_dropzones(actor="test-v12-6-1", root=root)
assert report["ingested_count"] >= 2

polish = narrative_dashboard_polish_payload(root=root, sort="confidence")
print(json.dumps(polish, indent=2))
assert polish["schema"] == "socmint.narrative_dashboard_polish.v12_6_1"
assert len(polish["events"]) >= 2
assert "claims_by_evidence" in polish
assert "contradiction_review_actions" in polish
assert "narrative_confidence_card" in polish

exports = write_story_exports(root=root)
print(json.dumps(exports, indent=2))
assert exports["schema"] == "socmint.narrative_export.v12_6_1"
assert Path(exports["json_path"]).exists()
assert Path(exports["markdown_path"]).exists()

story = dossier_story_layer(1, root=root)
print(json.dumps(story, indent=2))
assert story["schema"] == "socmint.dossier_auto_story.v12_6_1"
assert story["requires_human_review"] is True
print("PASS v12.6.1 narrative dashboard polish + dossier story export smoke")
PY
