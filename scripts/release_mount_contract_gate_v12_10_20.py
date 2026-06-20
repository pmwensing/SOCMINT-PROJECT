#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from src.socmint.release_mount_contract_v12_10_20 import release_mount_contract
from src.socmint.version import VERSION

REPORT_ROOT = Path("var/socmint/rc_reports")
REPORT_ROOT.mkdir(parents=True, exist_ok=True)

contract = release_mount_contract()
checks = {
    "version_is_12_10_20": VERSION == "12.10.20",
    "contract_paths_checked": contract["summary"]["required_count"] >= 4,
    "patch_guidance_available": "patch_guidance" in contract,
}
ok = all(checks.values()) and contract["status"] == "pass"

report = {
    "schema": "socmint.release_mount_contract_gate.v12_10_20",
    "version": "12.10.20",
    "generated_at": datetime.now(UTC).isoformat(),
    "status": "pass" if ok else "fail",
    "decision": "GO" if ok else "HOLD",
    "checks": checks,
    "contract": contract,
}

stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
json_path = REPORT_ROOT / f"socmint_v12_10_20_release_mount_contract_gate_{stamp}.json"
md_path = REPORT_ROOT / f"socmint_v12_10_20_release_mount_contract_gate_{stamp}.md"
json_path.write_text(json.dumps(report, indent=2, sort_keys=True))
md_path.write_text(
    "# SOCMINT v12.10.20 Release Mount Contract Gate\n\n"
    + f"- Status: `{report['status']}`\n- Decision: `{report['decision']}`\n"
)
print(json.dumps(report, indent=2, sort_keys=True))
sys.exit(0 if ok else 1)
