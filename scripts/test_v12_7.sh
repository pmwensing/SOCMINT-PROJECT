#!/usr/bin/env bash
set -euo pipefail

echo "[+] v12.7 authenticity anti-tamper integrity smoke"
rm -rf var/test_v12_7 || true
mkdir -p var/test_v12_7

PYTHONPATH=src python3 - <<'PY'
import json
from pathlib import Path
from src.socmint.forensic_intake_v12_5 import ensure_dropzones, dropzones_root, ingest_dropzones
from src.socmint.authenticity_integrity_v12_7 import integrity_dashboard_payload

root = "var/test_v12_7"
ensure_dropzones(root)
base = Path(dropzones_root(root))
(base / "images" / "screenshot_whatsapp.jpg").write_bytes(b"\xff\xd8\xff\xd9")
(base / "documents" / "generated_report.pdf").write_bytes(b"%PDF-1.4\n% test pdf\n")
(base / "video" / "clip.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42")
report = ingest_dropzones(actor="test-v12-7", root=root)
assert report["ingested_count"] >= 3
payload = integrity_dashboard_payload(root=root)
print(json.dumps(payload, indent=2))
assert payload["schema"] == "socmint.evidence_integrity_dashboard.v12_7"
assert payload["item_count"] >= 3
assert "summary" in payload
assert "analyses" in payload
assert all("authenticity" in item for item in payload["analyses"])
assert all("provenance_confidence" in item for item in payload["analyses"])
assert any(item["surface"] in {"screenshot", "pdf", "media"} for item in payload["analyses"])
assert len(payload["rules"]) >= 4
print("PASS v12.7 authenticity anti-tamper evidence integrity smoke")
PY
