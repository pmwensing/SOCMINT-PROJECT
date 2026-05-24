#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA = "socmint.release_status_live_smoke.v12_10_18"
VERSION = "12.10.18"
REPORT_ROOT = Path("var/socmint/rc_reports")


def now() -> str:
    return datetime.now(UTC).isoformat()


def check(rows: list[dict[str, Any]], name: str, ok: bool, detail: str = "") -> None:
    rows.append({"name": name, "status": "pass" if ok else "fail", "detail": detail})


def http_get(base_url: str, path: str) -> dict[str, Any]:
    url = base_url.rstrip("/") + path
    try:
        with urllib.request.urlopen(url, timeout=8) as response:
            body = response.read(300).decode("utf-8", errors="replace")
            return {"url": url, "ok": True, "status": int(response.status), "body_sample": body, "headers": dict(response.headers)}
    except urllib.error.HTTPError as exc:
        body = exc.read(300).decode("utf-8", errors="replace")
        return {"url": url, "ok": False, "status": int(exc.code), "body_sample": body, "headers": dict(exc.headers), "error": str(exc)}
    except Exception as exc:
        return {"url": url, "ok": False, "status": None, "body_sample": "", "headers": {}, "error": str(exc)}


def write_report(report: dict[str, Any]) -> dict[str, str]:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    jp = REPORT_ROOT / f"socmint_v12_10_18_release_status_live_smoke_{stamp}.json"
    mp = REPORT_ROOT / f"socmint_v12_10_18_release_status_live_smoke_{stamp}.md"
    jp.write_text(json.dumps(report, indent=2, sort_keys=True))
    lines = [
        "# SOCMINT v12.10.18 Release Status Live Smoke",
        "",
        f"- Status: `{report['status']}`",
        f"- Decision: `{report['decision']}`",
        f"- Base URL: `{report['base_url']}`",
        "",
        "## Checks",
        "",
    ]
    for row in report["checks"]:
        lines.append(f"- `{row['status']}` — {row['name']} — {row.get('detail', '')}")
    mp.write_text("\n".join(lines) + "\n")
    return {"json_path": str(jp), "markdown_path": str(mp)}


def run(base_url: str) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    try:
        from socmint.version import VERSION as package_version
        from socmint.wsgi import app
        routes = {rule.rule for rule in app.url_map.iter_rules()}
        check(checks, "package_version", package_version == VERSION, package_version)
        check(checks, "release_status_ui_route_registered", "/release/status" in routes, "/release/status")
        check(checks, "release_gates_ui_route_registered", "/release/gates" in routes, "/release/gates")
        check(checks, "release_status_api_route_registered", "/api/v1/release/status" in routes, "/api/v1/release/status")
        check(checks, "release_gates_api_route_registered", "/api/v1/release/gates/latest" in routes, "/api/v1/release/gates/latest")
    except Exception as exc:
        check(checks, "wsgi_route_import", False, str(exc))
        routes = set()

    templates = [
        Path("src/socmint/templates/release_status.html"),
        Path("src/socmint/templates/release_gates.html"),
    ]
    for template in templates:
        check(checks, f"template_exists:{template.name}", template.exists(), str(template))

    if base_url:
        ready = http_get(base_url, "/readyz")
        status_page = http_get(base_url, "/release/status")
        gates_page = http_get(base_url, "/release/gates")
        status_api = http_get(base_url, "/api/v1/release/status")
        gates_api = http_get(base_url, "/api/v1/release/gates/latest")
        check(checks, "live_readyz", ready.get("status") == 200, str(ready.get("status")))
        check(checks, "live_release_status_ui_protected", status_page.get("status") in {200, 302, 401}, str(status_page.get("status")))
        check(checks, "live_release_gates_ui_protected", gates_page.get("status") in {200, 302, 401}, str(gates_page.get("status")))
        check(checks, "live_release_status_api_auth_required", status_api.get("status") in {401, 403}, str(status_api.get("status")))
        check(checks, "live_release_gates_api_auth_required", gates_api.get("status") in {401, 403}, str(gates_api.get("status")))
        live = {"readyz": ready, "status_page": status_page, "gates_page": gates_page, "status_api": status_api, "gates_api": gates_api}
    else:
        live = {}

    failed = [row for row in checks if row["status"] != "pass"]
    report = {
        "schema": SCHEMA,
        "version": VERSION,
        "generated_at": now(),
        "base_url": base_url,
        "status": "pass" if not failed else "fail",
        "decision": "GO" if not failed else "HOLD",
        "checks": checks,
        "live": live,
    }
    report.update(write_report(report))
    return report


if __name__ == "__main__":
    base = os.getenv("SOCMINT_BASE_URL", "http://127.0.0.1:5000")
    result = run(base)
    print(json.dumps(result, indent=2, sort_keys=True))
    sys.exit(0 if result["status"] == "pass" else 1)
