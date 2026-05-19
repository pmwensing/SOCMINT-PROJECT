#!/usr/bin/env bash
set -euo pipefail

echo "[+] v12.9.1 command center guided flow integration smoke"
rm -rf var/test_v12_9_1 || true
mkdir -p var/test_v12_9_1

PYTHONPATH=src python3 - <<'PY'
import json
from pathlib import Path
from src.socmint.forensic_intake_v12_5 import ensure_dropzones, dropzones_root, ingest_dropzones
from src.socmint.guided_investigation_v12_9 import guided_investigation_payload
from src.socmint.production_release import production_release_check, production_release_summary

root = "var/test_v12_9_1"
ensure_dropzones(root)
base = Path(dropzones_root(root))
(base / "documents" / "flow_integration.txt").write_text("Command Center guided flow integration sample. analyst@example.com supports release workflow.\n")
(base / "images" / "screenshot_signal.jpg").write_bytes(b"\xff\xd8\xff\xd9")
report = ingest_dropzones(actor="test-v12-9-1", root=root)
assert report["ingested_count"] >= 2

flow = guided_investigation_payload(root=root)
print(json.dumps(flow, indent=2))
assert flow["schema"] == "socmint.guided_investigation.v12_9"
assert "progress_rail" in flow
assert "guided_assistant" in flow
assert "drilldowns" in flow

release = production_release_check()
print(json.dumps(release, indent=2))
assert release["schema"] == "socmint.production_release.v12_9_1"
assert release["version"] == "12.9.1"
assert "guided_workflow" in release
assert release["checks"].get("guided_workflow_available") is True

summary = production_release_summary()
print(json.dumps(summary, indent=2))
assert summary["schema"] == "socmint.production_release.v12_9_1"
assert "guided_workflow" in summary
assert any("Guided Investigation" in item for item in summary["milestones"])
print("PASS v12.9.1 command center flow integration smoke")
PY
