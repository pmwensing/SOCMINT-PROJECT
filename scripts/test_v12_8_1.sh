#!/usr/bin/env bash
set -euo pipefail

echo "[+] v12.8.1 assertion trust dossier gate smoke"
rm -rf var/test_v12_8_1 || true
mkdir -p var/test_v12_8_1

PYTHONPATH=src python3 - <<'PY'
import json
from pathlib import Path
from src.socmint.forensic_intake_v12_5 import ensure_dropzones, dropzones_root, ingest_dropzones
from src.socmint.assertion_trust_gate_v12_8_1 import assertion_trust_summary, assertion_release_gate, write_assertion_trust_report, assertion_command_center_card

root = "var/test_v12_8_1"
ensure_dropzones(root)
base = Path(dropzones_root(root))
(base / "documents" / "assertion_source.txt").write_text("Assertion trust gate sample: analyst@example.com supports the timeline claim.\n")
(base / "images" / "screenshot_signal.jpg").write_bytes(b"\xff\xd8\xff\xd9")
report = ingest_dropzones(actor="test-v12-8-1", root=root)
assert report["ingested_count"] >= 2

summary = assertion_trust_summary(root=root)
print(json.dumps(summary, indent=2))
assert summary["schema"] == "socmint.assertion_trust_gate.v12_8_1"
assert summary["assertion_count"] >= 1
assert "dossier_ready_assertions" in summary
assert "analyst_review_queue" in summary
assert all(float(row.get("trust_score") or 0) >= 0.5 for row in summary["dossier_ready_assertions"])

gate = assertion_release_gate(root=root)
print(json.dumps(gate, indent=2))
assert gate["schema"] == "socmint.assertion_trust_gate.v12_8_1"
assert gate["release_gate_decision"] in {"GO", "HOLD", "FAIL"}
assert any(check["name"] == "no_hold_assertions" for check in gate["checks"])
assert any(check["name"] == "low_confidence_excluded_from_dossier_ready" for check in gate["checks"])

card = assertion_command_center_card(root=root)
print(json.dumps(card, indent=2))
assert card["schema"] == "socmint.command_center_assertion_trust_card.v12_8_1"

export = write_assertion_trust_report(root=root)
print(json.dumps(export, indent=2))
assert export["schema"] == "socmint.assertion_trust_report.v12_8_1"
assert Path(export["json_path"]).exists()
assert Path(export["markdown_path"]).exists()
print("PASS v12.8.1 assertion trust dossier gate smoke")
PY
