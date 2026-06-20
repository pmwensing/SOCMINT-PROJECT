#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

for candidate in ("/app/src", "/app", ".", "./src"):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

try:
    from socmint.release_runtime_readiness_v12_10_21 import release_runtime_readiness
    from socmint.release_status_v12_10_19 import release_status
    from socmint.version import VERSION
except ModuleNotFoundError:
    from src.socmint.release_runtime_readiness_v12_10_21 import (
        release_runtime_readiness,
    )
    from src.socmint.release_status_v12_10_19 import release_status
    from src.socmint.version import VERSION


def _report_root() -> Path:
    candidates = [
        os.getenv("SOCMINT_RC_REPORT_DIR"),
        "var/socmint/rc_reports",
        "/tmp/socmint/rc_reports",
    ]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate)
        try:
            path.mkdir(parents=True, exist_ok=True)
            probe = path / ".write_probe"
            probe.write_text("ok")
            probe.unlink(missing_ok=True)
            return path
        except Exception:
            continue
    raise PermissionError("No writable SOCMINT report directory found")


REPORT_ROOT = _report_root()

runtime = release_runtime_readiness()
status = release_status()

checks = {
    "version_is_12_10_21": VERSION == "12.10.21",
    "local_runtime_ready": bool(runtime.get("local_runtime_ready")),
    "readyz_http_ok": bool(runtime.get("checks", {}).get("local_readyz_http")),
    "dashboard_http_ok": bool(runtime.get("checks", {}).get("local_dashboard_http")),
    "tor_nonblocking_policy": runtime.get("policy", {}).get(
        "tor_file_visibility_blocks_release_status"
    )
    is False,
    "release_status_go": status.get("decision") == "GO",
}

ok = all(checks.values())

report = {
    "schema": "socmint.release_runtime_readiness_gate.v12_10_21",
    "version": "12.10.21",
    "generated_at": datetime.now(UTC).isoformat(),
    "status": "pass" if ok else "fail",
    "decision": "GO" if ok else "HOLD",
    "checks": checks,
    "runtime": runtime,
    "release_status": {
        "status": status.get("status"),
        "decision": status.get("decision"),
        "checks": status.get("checks"),
        "sections": status.get("sections"),
    },
}

stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
json_path = (
    REPORT_ROOT / f"socmint_v12_10_21_release_runtime_readiness_gate_{stamp}.json"
)
md_path = REPORT_ROOT / f"socmint_v12_10_21_release_runtime_readiness_gate_{stamp}.md"
json_path.write_text(json.dumps(report, indent=2, sort_keys=True))
md_path.write_text(
    "# SOCMINT v12.10.21 Release Runtime Readiness Gate\n\n"
    f"- Status: `{report['status']}`\n"
    f"- Decision: `{report['decision']}`\n"
)

print(json.dumps(report, indent=2, sort_keys=True))
sys.exit(0 if ok else 1)
