#!/usr/bin/env bash
set -euo pipefail

echo "[+] v12.9 guided investigation flow smoke"
rm -rf var/test_v12_9 || true
mkdir -p var/test_v12_9

PYTHONPATH=src python3 - <<'PY'
import json
from pathlib import Path
from src.socmint.forensic_intake_v12_5 import ensure_dropzones, dropzones_root, ingest_dropzones
from src.socmint.guided_investigation_v12_9 import guided_investigation_payload

root = "var/test_v12_9"
ensure_dropzones(root)
base = Path(dropzones_root(root))
(base / "documents" / "guided_source.txt").write_text("Guided investigation sample. analyst@example.com supports timeline and assertion review.\n")
(base / "images" / "screenshot_signal.jpg").write_bytes(b"\xff\xd8\xff\xd9")
report = ingest_dropzones(actor="test-v12-9", root=root)
assert report["ingested_count"] >= 2

payload = guided_investigation_payload(root=root)
print(json.dumps(payload, indent=2))
assert payload["schema"] == "socmint.guided_investigation.v12_9"
assert payload["readiness"] in {"red", "yellow", "green"}
assert len(payload["progress_rail"]) >= 5
assert {step["key"] for step in payload["progress_rail"]} >= {"evidence", "integrity", "narrative", "assertions", "release"}
assert "flow_map" in payload
assert len(payload["flow_map"]["edges"]) >= 4
assert "action_queue" in payload
assert "next_action" in payload
assert "guided_assistant" in payload
assert "drilldowns" in payload
print("PASS v12.9 guided investigation visual command center smoke")
PY
