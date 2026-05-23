#!/usr/bin/env bash
set -euo pipefail

echo "[+] v12.8 cross-source corroboration assertion trust smoke"
rm -rf var/test_v12_8 || true
mkdir -p var/test_v12_8

PYTHONPATH=src python3 - <<'PY'
import json
from pathlib import Path
from src.socmint.forensic_intake_v12_5 import ensure_dropzones, dropzones_root, ingest_dropzones
from src.socmint.assertion_trust_v12_8 import build_assertion_trust, corroboration_dashboard_payload

root = "var/test_v12_8"
ensure_dropzones(root)
base = Path(dropzones_root(root))
(base / "documents" / "claim_source.txt").write_text("Claim source: analyst@example.com stated the preserved document supports the timeline. Phone 613-555-0101 mentioned.\n")
(base / "images" / "screenshot_signal.jpg").write_bytes(b"\xff\xd8\xff\xd9")
report = ingest_dropzones(actor="test-v12-8", root=root)
assert report["ingested_count"] >= 2

trust = build_assertion_trust(root=root)
print(json.dumps(trust, indent=2))
assert trust["schema"] == "socmint.assertion_trust.v12_8"
assert trust["assertion_count"] >= 1
assert "summary" in trust
assert all("trust_score" in row for row in trust["assertions"])
assert all(row["release_state"] in {"dossier-ready", "analyst-review", "hold", "low-confidence"} for row in trust["assertions"])
assert "integrity_drilldown" in trust

dashboard = corroboration_dashboard_payload(root=root)
print(json.dumps(dashboard, indent=2))
assert dashboard["schema"] == "socmint.corroboration_dashboard.v12_8"
assert "top_assertions" in dashboard
assert "review_queue" in dashboard
print("PASS v12.8 cross-source corroboration assertion trust smoke")
PY
