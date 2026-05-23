#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA = "socmint.release.runtime_route_gate.v12_10_14"
VERSION = "12.10.14"

REQUIRED_ROUTES = [
    "/api/v1/recon/document-locator/search",
    "/recon/document-locator",
    "/forensic/intake",
    "/api/v1/forensic/intake",
    "/evidence/integrity",
    "/api/v1/evidence/integrity",
    "/evidence/integrity/gate",
    "/api/v1/evidence/integrity/gate",
    "/narrative/storyboard",
    "/api/v1/narrative/story-reconstruction",
    "/api/v1/narrative/story-polish",
    "/api/v1/narrative/story-export",
    "/assertions/trust",
    "/api/v1/assertions/trust",
    "/assertions/trust/gate",
    "/api/v1/assertions/trust/gate",
    "/investigation/flow",
    "/api/v1/investigation/flow",
    "/command-center",
    "/api/v1/command-center",
    "/api/v1/spine/subjects/<int:subject_id>/full-report",
    "/api/v1/spine/subjects/<int:subject_id>/full-report/run",
    "/api/v1/spine/subjects/<int:subject_id>/full-report/latest",
    "/api/v1/spine/subjects/<int:subject_id>/full-report/download",
]


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def write_report(report: dict[str, Any], root: str = "var/socmint/rc_reports") -> dict[str, str]:
    out = Path(root)
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    json_path = out / f"socmint_v12_10_14_runtime_route_gate_{stamp}.json"
    md_path = out / f"socmint_v12_10_14_runtime_route_gate_{stamp}.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True))
    lines = [
        "# SOCMINT v12.10.14 Runtime Route Release Gate",
        "",
        f"- Schema: `{report['schema']}`",
        f"- Version: `{report['version']}`",
        f"- Generated: `{report['generated_at']}`",
        f"- Status: `{report['status']}`",
        f"- Decision: `{report['decision']}`",
        f"- Available routes: `{report.get('available_count')}`",
        f"- Missing routes: `{len(report.get('missing_routes', []))}`",
        "",
        "## Required Route Results",
        "",
    ]
    for row in report.get("routes", []):
        lines.append(f"- `{row['status']}` — `{row['route']}`")
    if report.get("error"):
        lines.extend(["", "## Error", "", f"```text\n{report['error']}\n```"])
    md_path.write_text("\n".join(lines) + "\n")
    return {"json_path": str(json_path), "markdown_path": str(md_path)}


def run_gate() -> dict[str, Any]:
    try:
        from socmint.version import VERSION as package_version
        from socmint.wsgi import app
    except Exception as exc:
        report = {
            "schema": SCHEMA,
            "version": VERSION,
            "generated_at": utc_now(),
            "status": "fail",
            "decision": "FAIL",
            "package_version": None,
            "error": f"WSGI app import failed: {exc}",
            "routes": [{"route": route, "status": "not_checked"} for route in REQUIRED_ROUTES],
            "missing_routes": REQUIRED_ROUTES,
            "available_count": 0,
        }
        report.update(write_report(report))
        return report

    available = {rule.rule for rule in app.url_map.iter_rules()}
    rows = [{"route": route, "status": "pass" if route in available else "missing"} for route in REQUIRED_ROUTES]
    missing = [row["route"] for row in rows if row["status"] != "pass"]
    version_match = package_version == VERSION
    status = "pass" if not missing and version_match else "fail"
    report = {
        "schema": SCHEMA,
        "version": VERSION,
        "generated_at": utc_now(),
        "status": status,
        "decision": "GO" if status == "pass" else "FAIL",
        "package_version": package_version,
        "version_match": version_match,
        "routes": rows,
        "missing_routes": missing,
        "available_count": len(available),
    }
    report.update(write_report(report))
    return report


if __name__ == "__main__":
    result = run_gate()
    print(json.dumps(result, indent=2, sort_keys=True))
    sys.exit(0 if result.get("status") == "pass" else 1)
