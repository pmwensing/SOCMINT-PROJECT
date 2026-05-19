#!/usr/bin/env bash
set -euo pipefail

echo "[+] v12.10 RC hardening regression gate smoke"
rm -rf var/test_v12_10 || true
mkdir -p var/test_v12_10

PYTHONPATH=src python3 - <<'PY'
import json
from pathlib import Path
from src.socmint.forensic_intake_v12_5 import ensure_dropzones, dropzones_root, ingest_dropzones
from src.socmint.rc_regression_gate_v12_10 import import_audit, payload_audit, rc_regression_report, route_audit, write_rc_report

root = "var/test_v12_10"
ensure_dropzones(root)
base = Path(dropzones_root(root))
(base / "documents" / "rc_gate.txt").write_text("RC regression gate sample. analyst@example.com supports guided workflow verification.\n")
(base / "images" / "screenshot_signal.jpg").write_bytes(b"\xff\xd8\xff\xd9")
report = ingest_dropzones(actor="test-v12-10", root=root)
assert report["ingested_count"] >= 2

imports = import_audit()
print(json.dumps(imports, indent=2))
assert imports["schema"] == "socmint.rc_regression_gate.v12_10"
assert imports["status"] in {"pass", "fail"}
assert len(imports["modules"]) >= 8

routes = route_audit()
print(json.dumps(routes, indent=2))
assert routes["schema"] == "socmint.rc_regression_gate.v12_10"
assert routes["routes"], "route audit must return route rows even when app import is review-only"
assert any(row["route"] == "/investigation/flow" for row in routes["routes"])
assert routes["status"] in {"pass", "fail", "review"}

payloads = payload_audit()
print(json.dumps(payloads, indent=2))
assert payloads["schema"] == "socmint.rc_regression_gate.v12_10"
assert any(row["name"] == "command_center_payload" for row in payloads["checks"])
assert any(row["name"] == "guided_investigation_payload" for row in payloads["checks"])
assert payloads["status"] in {"pass", "fail"}

rc = rc_regression_report()
print(json.dumps(rc, indent=2))
assert rc["schema"] == "socmint.rc_regression_gate.v12_10"
assert rc["decision"] in {"GO", "HOLD", "FAIL"}
assert "import_audit" in rc and "route_audit" in rc and "payload_audit" in rc and "smoke_targets" in rc

export = write_rc_report(root="var/test_v12_10/reports")
print(json.dumps(export, indent=2))
assert Path(export["json_path"]).exists()
assert Path(export["markdown_path"]).exists()
print("PASS v12.10 RC hardening regression gate smoke")
PY
