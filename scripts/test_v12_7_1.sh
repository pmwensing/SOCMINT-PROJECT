#!/usr/bin/env bash
set -euo pipefail

echo "[+] v12.7.1 integrity dossier gate smoke"
rm -rf var/test_v12_7_1 || true
mkdir -p var/test_v12_7_1

PYTHONPATH=src python3 - <<'PY'
import json
from pathlib import Path
from src.socmint.forensic_intake_v12_5 import ensure_dropzones, dropzones_root, ingest_dropzones
from src.socmint.integrity_gate_v12_7_1 import evidence_integrity_summary, integrity_release_gate, write_integrity_report, integrity_drilldown_for_claims

root = "var/test_v12_7_1"
ensure_dropzones(root)
base = Path(dropzones_root(root))
(base / "images" / "screenshot_signal.jpg").write_bytes(b"\xff\xd8\xff\xd9")
(base / "documents" / "source_note.txt").write_text("Evidence integrity claim drilldown sample.\n")
report = ingest_dropzones(actor="test-v12-7-1", root=root)
assert report["ingested_count"] >= 2

summary = evidence_integrity_summary(root=root)
print(json.dumps(summary, indent=2))
assert summary["schema"] == "socmint.integrity_gate.v12_7_1"
assert summary["item_count"] >= 2
assert "item_decisions" in summary
assert all(item["usable_state"] in {"usable", "review", "hold"} for item in summary["item_decisions"])

gate = integrity_release_gate(root=root)
print(json.dumps(gate, indent=2))
assert gate["schema"] == "socmint.integrity_gate.v12_7_1"
assert gate["release_gate_decision"] in {"GO", "HOLD", "FAIL"}
assert any(check["name"] == "no_critical_hash_mismatch" for check in gate["checks"])
assert any(check["name"] == "flagged_evidence_requires_review" for check in gate["checks"])

claims_by_evidence = {summary["item_decisions"][0]["evidence_id"]: [{"claim_id": "c1", "predicate": "sample", "value": "true"}]}
drilldown = integrity_drilldown_for_claims(claims_by_evidence, root=root)
print(json.dumps(drilldown, indent=2))
assert drilldown["rows"][0]["integrity"]["usable_state"] in {"usable", "review", "hold"}

export = write_integrity_report(root=root)
print(json.dumps(export, indent=2))
assert export["schema"] == "socmint.integrity_report_export.v12_7_1"
assert Path(export["json_path"]).exists()
assert Path(export["markdown_path"]).exists()
print("PASS v12.7.1 integrity dossier gate upgrade smoke")
PY
