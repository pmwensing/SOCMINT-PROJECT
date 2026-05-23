#!/usr/bin/env bash
set -euo pipefail

echo "[+] v12.3.1 document locator smoke"
PYTHONPATH=src python3 - <<'PY'
import json
from pathlib import Path
from src.socmint.recon_document_locator import document_locator_search, queue_for_manual_acquisition

report = document_locator_search("example.com")
print(json.dumps(report, indent=2))
assert report["schema"] == "socmint.recon.document_locator.v12_3_1"
assert report["recommended_default_backend"] == "brave"
assert len(report["dork_templates"]) >= 6
assert report["result_count"] >= 1
first = report["results"][0]
assert "legal_safety" in first
queued = queue_for_manual_acquisition(first, actor="test-v12-3-1", root="var/test_v12_3_1")
assert queued["queue_count"] >= 1
assert Path(queued["queue_path"]).exists()
print("PASS v12.3.1 document locator connector framework smoke")
PY
