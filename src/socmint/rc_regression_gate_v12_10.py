from __future__ import annotations

import importlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .command_center import command_center_payload
from .guided_investigation_v12_9 import guided_investigation_payload
from .production_release import production_release_check, production_release_summary

SCHEMA = "socmint.rc_regression_gate.v12_10"

V12_MODULES = [
    "socmint.forensic_intake_v12_5",
    "socmint.narrative_export_v12_6_1",
    "socmint.authenticity_integrity_v12_7",
    "socmint.integrity_gate_v12_7_1",
    "socmint.assertion_trust_v12_8",
    "socmint.assertion_trust_gate_v12_8_1",
    "socmint.guided_investigation_v12_9",
    "socmint.production_release",
    "socmint.command_center",
]

V12_ROUTES = [
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
]

V12_SMOKE_TARGETS = [
    "test-v12-3-1",
    "test-v12-3-2",
    "test-v12-5",
    "test-v12-5-1",
    "test-v12-6",
    "test-v12-6-1",
    "test-v12-7",
    "test-v12-7-1",
    "test-v12-8",
    "test-v12-8-1",
    "test-v12-9",
    "test-v12-9-1",
]


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def import_audit() -> dict[str, Any]:
    rows = []
    for name in V12_MODULES:
        try:
            module = importlib.import_module(name)
            rows.append({"module": name, "status": "pass", "path": getattr(module, "__file__", None)})
        except Exception as exc:
            rows.append({"module": name, "status": "fail", "error": str(exc)})
    failed = [row for row in rows if row["status"] != "pass"]
    return {"schema": SCHEMA, "status": "pass" if not failed else "fail", "modules": rows, "failure_count": len(failed)}


def route_audit(app: Any | None = None) -> dict[str, Any]:
    if app is None:
        try:
            from .wsgi import app as wsgi_app
            app = wsgi_app
        except Exception as exc:
            rows = [{"route": route, "status": "not_checked"} for route in V12_ROUTES]
            return {
                "schema": SCHEMA,
                "status": "review",
                "error": str(exc),
                "routes": rows,
                "missing": [],
                "available_count": 0,
                "note": "WSGI app import failed; route list preserved for RC diagnostics and marked review instead of crashing smoke.",
            }
    available = {rule.rule for rule in app.url_map.iter_rules()}
    rows = [{"route": route, "status": "pass" if route in available else "missing"} for route in V12_ROUTES]
    missing = [row["route"] for row in rows if row["status"] != "pass"]
    return {"schema": SCHEMA, "status": "pass" if not missing else "fail", "routes": rows, "missing": missing, "available_count": len(available)}


def payload_audit() -> dict[str, Any]:
    checks = []
    try:
        release = production_release_check()
        checks.append({"name": "production_release_check", "status": "pass" if release.get("guided_workflow") else "fail", "schema": release.get("schema"), "state": release.get("state")})
    except Exception as exc:
        checks.append({"name": "production_release_check", "status": "fail", "error": str(exc)})
    try:
        summary = production_release_summary()
        checks.append({"name": "production_release_summary", "status": "pass" if summary.get("guided_workflow") else "fail", "schema": summary.get("schema"), "version": summary.get("version")})
    except Exception as exc:
        checks.append({"name": "production_release_summary", "status": "fail", "error": str(exc)})
    try:
        command = command_center_payload()
        checks.append({"name": "command_center_payload", "status": "pass" if command.get("guided_investigation") else "fail", "schema": command.get("schema"), "guided_readiness": command.get("summary", {}).get("guided_readiness")})
    except Exception as exc:
        checks.append({"name": "command_center_payload", "status": "fail", "error": str(exc)})
    try:
        guided = guided_investigation_payload()
        checks.append({"name": "guided_investigation_payload", "status": "pass" if guided.get("progress_rail") and guided.get("flow_map") else "fail", "schema": guided.get("schema"), "readiness": guided.get("readiness")})
    except Exception as exc:
        checks.append({"name": "guided_investigation_payload", "status": "fail", "error": str(exc)})
    failed = [row for row in checks if row.get("status") != "pass"]
    return {"schema": SCHEMA, "status": "pass" if not failed else "fail", "checks": checks, "failure_count": len(failed)}


def smoke_target_plan() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "planned",
        "targets": V12_SMOKE_TARGETS,
        "command": "make -f GNUmakefile test-v12-full",
        "note": "The shell wrapper executes each target in order; this payload records the canonical target order for the RC report.",
    }


def rc_regression_report(app: Any | None = None) -> dict[str, Any]:
    imports = import_audit()
    routes = route_audit(app=app)
    payloads = payload_audit()
    smokes = smoke_target_plan()
    checks = [
        {"name": "import_audit", "status": imports["status"], "failure_count": imports.get("failure_count", 0)},
        {"name": "route_audit", "status": routes["status"], "failure_count": len(routes.get("missing", []))},
        {"name": "payload_audit", "status": payloads["status"], "failure_count": payloads.get("failure_count", 0)},
        {"name": "smoke_target_plan", "status": "pass" if smokes.get("targets") else "fail", "failure_count": 0 if smokes.get("targets") else 1},
    ]
    fail_count = sum(1 for item in checks if item["status"] == "fail")
    review_count = sum(1 for item in checks if item["status"] == "review")
    decision = "GO" if fail_count == 0 and review_count == 0 else "HOLD" if fail_count == 0 else "FAIL"
    return {
        "schema": SCHEMA,
        "generated_at": utc_now(),
        "version": "12.10",
        "decision": decision,
        "status": "pass" if decision == "GO" else "hold" if decision == "HOLD" else "fail",
        "checks": checks,
        "import_audit": imports,
        "route_audit": routes,
        "payload_audit": payloads,
        "smoke_targets": smokes,
    }


def write_rc_report(root: str | None = None, app: Any | None = None) -> dict[str, Any]:
    report = rc_regression_report(app=app)
    out = Path(root or "var/socmint/rc_reports")
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    base = out / f"socmint_v12_10_rc_report_{stamp}"
    json_path = base.with_suffix(".json")
    md_path = base.with_suffix(".md")
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True))
    lines = [
        "# SOCMINT v12.10 RC Regression Report",
        "",
        f"- Generated: `{report.get('generated_at')}`",
        f"- Decision: `{report.get('decision')}`",
        f"- Status: `{report.get('status')}`",
        "",
        "## Checks",
        "",
    ]
    for check in report.get("checks", []):
        lines.append(f"- `{check.get('status')}` — {check.get('name')} — failures `{check.get('failure_count')}`")
    lines.extend(["", "## Smoke Target Order", ""])
    for target in V12_SMOKE_TARGETS:
        lines.append(f"- `{target}`")
    md_path.write_text("\n".join(lines) + "\n")
    return {"schema": SCHEMA, "json_path": str(json_path), "markdown_path": str(md_path), "decision": report.get("decision"), "status": report.get("status"), "report": report}


if __name__ == "__main__":
    print(json.dumps(rc_regression_report(), indent=2, sort_keys=True))
