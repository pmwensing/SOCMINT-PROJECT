#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT_JSON = ROOT / "release/v12_10_54D/RUNTIME_APP_DISCOVERY_REPORT_V12_10_54D.json"
OUT_MD = ROOT / "release/v12_10_54D/RUNTIME_APP_DISCOVERY_REPORT_V12_10_54D.md"
TRACE_TXT = ROOT / "release/v12_10_54G/RUNTIME_APP_DISCOVERY_TRACE_V12_10_54G.txt"

EXPECTED_ENDPOINTS = [
    "/api/version",
    "/api/schema/status",
    "/api/schema/upgrade-guard",
    "/api/release/archive-integrity",
    "/api/schema/rollback/0018",
]


def trace(title: str, content: str) -> None:
    TRACE_TXT.parent.mkdir(parents=True, exist_ok=True)
    with TRACE_TXT.open("a") as f:
        f.write("\n\n" + title + "\n")
        f.write("=" * len(title) + "\n")
        f.write(content)
        f.write("\n")


def get_dashboard_app() -> tuple[Any | None, str, list[str]]:
    traces: list[str] = []

    try:
        from src.socmint.v12_10_54_app_adapter import get_hardened_dashboard_app

        return get_hardened_dashboard_app(), "dashboard_runtime", traces
    except Exception:
        traces.append("dashboard_runtime failed:\n" + traceback.format_exc())

    return None, "dashboard_runtime_failed", traces


def get_isolated_probe_app() -> tuple[Any | None, str, list[str]]:
    traces: list[str] = []

    try:
        from flask import Flask
        from src.socmint.v12_10_54_runtime_guard_routes import register_v12_10_54_routes

        app = Flask("v12_10_54_isolated_probe")
        register_v12_10_54_routes(app)
        return app, "isolated_probe", traces
    except Exception:
        traces.append("isolated_probe failed:\n" + traceback.format_exc())
        return None, "isolated_probe_failed", traces


def probe_endpoints(app: Any) -> tuple[dict[str, Any], list[str]]:
    client = app.test_client()
    endpoint_results: dict[str, Any] = {}
    errors: list[str] = []

    for path in EXPECTED_ENDPOINTS:
        try:
            res = client.get(path)
            body = res.get_json(silent=True)
            endpoint_results[path] = {
                "status_code": res.status_code,
                "json": body,
                "body_preview": res.get_data(as_text=True)[:800],
            }
            if res.status_code != 200:
                errors.append(f"{path} returned {res.status_code}")
        except Exception:
            endpoint_results[path] = {
                "status_code": None,
                "json": None,
                "body_preview": "",
                "exception": traceback.format_exc(),
            }
            errors.append(f"{path} request crashed")

    version_json = endpoint_results.get("/api/version", {}).get("json") or {}
    if version_json.get("version") != "12.10.54":
        errors.append(f"/api/version expected 12.10.54, got {version_json.get('version')}")

    schema_json = endpoint_results.get("/api/schema/status", {}).get("json") or {}
    if schema_json.get("real_db_upgrade_default_blocked") is not True:
        errors.append("/api/schema/status did not confirm real_db_upgrade_default_blocked=True")
    if schema_json.get("production_db_touched") is not False:
        errors.append("/api/schema/status did not confirm production_db_touched=False")
    if schema_json.get("real_config_upgrade_run") is not False:
        errors.append("/api/schema/status did not confirm real_config_upgrade_run=False")

    guard_json = endpoint_results.get("/api/schema/upgrade-guard", {}).get("json") or {}
    if guard_json.get("allowed") is not False:
        errors.append("/api/schema/upgrade-guard should be blocked by default")

    archive_json = endpoint_results.get("/api/release/archive-integrity", {}).get("json") or {}
    if archive_json.get("integrity_ok") is not True:
        errors.append("/api/release/archive-integrity did not return integrity_ok=True")

    rollback_json = endpoint_results.get("/api/schema/rollback/0018", {}).get("json") or {}
    if rollback_json.get("rollback_to") != "0017_v12_10_schema_reconciliation":
        errors.append("/api/schema/rollback/0018 rollback target mismatch")

    return endpoint_results, errors


def main() -> int:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    TRACE_TXT.parent.mkdir(parents=True, exist_ok=True)
    TRACE_TXT.write_text("v12.10.54G runtime discovery trace\n")

    traces: list[str] = []
    errors: list[str] = []
    warnings: list[str] = []
    endpoint_results: dict[str, Any] = {}

    app, mode, app_traces = get_dashboard_app()
    traces.extend(app_traces)

    if app is None:
        warnings.append("dashboard runtime discovery failed; using isolated route probe fallback")
        app, mode, probe_traces = get_isolated_probe_app()
        traces.extend(probe_traces)

    if app is None:
        errors.append("could not create dashboard runtime app or isolated probe app")
    else:
        endpoint_results, endpoint_errors = probe_endpoints(app)
        errors.extend(endpoint_errors)

    for idx, tb in enumerate(traces, 1):
        trace(f"traceback {idx}", tb)

    report = {
        "version": "12.10.54G",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "GO" if not errors else "NO-GO",
        "verification_mode": mode,
        "endpoint_results": endpoint_results,
        "endpoint_count": len(endpoint_results),
        "expected_endpoint_count": len(EXPECTED_ENDPOINTS),
        "errors": errors,
        "warnings": warnings,
        "trace_file": str(TRACE_TXT),
        "tracebacks": traces,
        "production_db_touched": False,
        "real_config_upgrade_run": False,
    }

    OUT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True))
    write_md(report)

    print(json.dumps({
        "version": "12.10.54G",
        "status": report["status"],
        "verification_mode": mode,
        "endpoint_count": len(endpoint_results),
        "expected_endpoint_count": len(EXPECTED_ENDPOINTS),
        "error_count": len(errors),
        "warning_count": len(warnings),
        "trace_file": str(TRACE_TXT),
        "production_db_touched": False,
        "real_config_upgrade_run": False,
        "report_json": str(OUT_JSON),
        "report_md": str(OUT_MD),
    }, indent=2, sort_keys=True))

    return 0 if not errors else 1


def write_md(report: dict[str, Any]) -> None:
    lines = [
        "# v12.10.54G Runtime App Discovery Report",
        "",
        f"- **status**: `{report['status']}`",
        f"- **verification_mode**: `{report['verification_mode']}`",
        f"- **endpoint_count**: `{report['endpoint_count']}`",
        f"- **expected_endpoint_count**: `{report['expected_endpoint_count']}`",
        "- **production_db_touched**: `False`",
        "- **real_config_upgrade_run**: `False`",
        f"- **trace_file**: `{report['trace_file']}`",
        "",
        "## Endpoint results",
        "",
    ]

    for path, result in report["endpoint_results"].items():
        lines.append(f"- `{path}`: `{result['status_code']}`")

    lines.extend(["", "## Errors", ""])
    if report["errors"]:
        lines.extend(f"- {err}" for err in report["errors"])
    else:
        lines.append("- none")

    lines.extend(["", "## Warnings", ""])
    if report["warnings"]:
        lines.extend(f"- {w}" for w in report["warnings"])
    else:
        lines.append("- none")

    if report["tracebacks"]:
        lines.extend(["", "## Tracebacks", ""])
        for tb in report["tracebacks"]:
            lines.extend(["```text", tb[-6000:], "```"])

    OUT_MD.write_text("\n".join(lines))


if __name__ == "__main__":
    raise SystemExit(main())
