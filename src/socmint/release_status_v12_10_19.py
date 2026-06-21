from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .tor_production import tor_hidden_service_diagnostics
from .release_runtime_readiness_v12_10_21 import release_runtime_readiness
from .version import (
    RELEASE_CHANNEL,
    RELEASE_NAME,
    RELEASE_TAG,
    VERSION,
    version_payload,
)

SCHEMA = "socmint.release_status.v12_10_21"
GATES_SCHEMA = "socmint.release_gates.latest.v12_10_21"
DEFAULT_REPORT_ROOT = Path("var/socmint/rc_reports")
PASS_DECISIONS = {"GO", "PASS", None, ""}


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _truthy_env(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"parse_error": str(exc)}


def _summary(path: Path) -> dict[str, Any]:
    stat = path.stat()
    data = _json(path) if path.suffix == ".json" else {}
    return {
        "path": str(path),
        "name": path.name,
        "exists": True,
        "size_bytes": stat.st_size,
        "modified_at_epoch": stat.st_mtime,
        "schema": data.get("schema"),
        "status": data.get("status"),
        "decision": data.get("decision"),
        "version": data.get("version"),
        "generated_at": data.get("generated_at"),
        "parse_error": data.get("parse_error"),
    }


def _is_pass(row: dict[str, Any]) -> bool:
    return row.get("status") == "pass" and row.get("decision") in PASS_DECISIONS


def _is_release_gate(row: dict[str, Any]) -> bool:
    text = f"{row.get('schema') or ''} {row.get('name') or ''}"
    return "runtime_route_gate" in text or "post_merge_master_verify" in text


def latest_gate_reports(
    report_root: str | Path = DEFAULT_REPORT_ROOT,
) -> dict[str, Any]:
    root = Path(report_root)
    if not root.exists():
        return {
            "schema": GATES_SCHEMA,
            "generated_at": utc_now(),
            "status": "missing_reports",
            "decision": "HOLD",
            "report_root": str(root),
            "latest": None,
            "latest_overall": None,
            "latest_pass": None,
            "latest_release_gate_pass": None,
            "reports": [],
            "report_count": 0,
        }
    files = sorted(
        [p for p in root.glob("*.json") if p.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    reports = [_summary(p) for p in files[:40]]
    latest_overall = reports[0] if reports else None
    pass_reports = [row for row in reports if _is_pass(row)]
    latest_pass = pass_reports[0] if pass_reports else None
    gate_passes = [row for row in pass_reports if _is_release_gate(row)]
    latest_release_gate_pass = gate_passes[0] if gate_passes else latest_pass
    ok = latest_release_gate_pass is not None
    return {
        "schema": GATES_SCHEMA,
        "generated_at": utc_now(),
        "status": "pass"
        if ok
        else "needs_review"
        if latest_overall
        else "missing_reports",
        "decision": "GO" if ok else "HOLD",
        "report_root": str(root),
        "latest": latest_release_gate_pass or latest_overall,
        "latest_overall": latest_overall,
        "latest_pass": latest_pass,
        "latest_release_gate_pass": latest_release_gate_pass,
        "reports": reports,
        "report_count": len(files),
        "failed_latest_does_not_block": bool(
            latest_overall and latest_pass and not _is_pass(latest_overall)
        ),
    }


def _manifest(root: str | Path = ".") -> dict[str, Any]:
    path = Path(root) / "release" / "CURRENT_STATUS.json"
    if not path.exists():
        return {
            "exists": False,
            "path": str(path),
            "error": "missing release/CURRENT_STATUS.json",
        }
    data = _json(path)
    data["exists"] = True
    data["path"] = str(path)
    return data


def runtime_health() -> dict[str, Any]:
    if _truthy_env("SOCMINT_RELEASE_DASHBOARD_ASSUME_RUNTIME_READY"):
        return {
            "schema": "socmint.runtime_health.override.v12_10_19",
            "status": "pass",
            "decision": "GO",
            "checks": {
                "app_socket_listening": True,
                "readyz_http_ok": True,
                "dashboard_http_ok": True,
                "torrc_available_to_process": False,
                "hidden_service_dir_present": False,
                "hostname_present": False,
            },
            "runtime_ready": True,
            "file_visibility_ready": False,
            "dashboard_blocking": False,
            "status_for_dashboard": "pass",
            "decision_for_dashboard": "GO",
            "override": True,
            "override_reason": "SOCMINT_RELEASE_DASHBOARD_ASSUME_RUNTIME_READY was set for CI/offline verification.",
        }
    try:
        diag = tor_hidden_service_diagnostics()
    except Exception as exc:
        return {
            "status": "needs_review",
            "decision": "HOLD",
            "error": str(exc),
            "checks": {},
            "runtime_ready": False,
            "file_visibility_ready": False,
        }
    checks = diag.get("checks", {}) or {}
    runtime_ready = bool(
        checks.get("app_socket_listening")
        and checks.get("readyz_http_ok")
        and checks.get("dashboard_http_ok")
    )
    file_visibility_ready = bool(
        checks.get("torrc_available_to_process")
        and checks.get("hidden_service_dir_present")
        and checks.get("hostname_present")
    )
    diag["runtime_ready"] = runtime_ready
    diag["file_visibility_ready"] = file_visibility_ready
    diag["dashboard_blocking"] = False
    diag["status_for_dashboard"] = "pass" if runtime_ready else "needs_review"
    diag["decision_for_dashboard"] = "GO" if runtime_ready else "HOLD"
    return diag


def release_status(
    root: str | Path = ".", report_root: str | Path = DEFAULT_REPORT_ROOT
) -> dict[str, Any]:
    manifest = _manifest(root)
    gates = latest_gate_reports(report_root)
    legacy_runtime = runtime_health()
    split_runtime = release_runtime_readiness()
    runtime = {
        **legacy_runtime,
        **split_runtime,
        "legacy_tor_diagnostics": legacy_runtime,
    }
    required = [
        "release/CURRENT_STATUS.json",
        "release/V12_10_18_RELEASE_STATUS_DASHBOARD_UI.md",
        "src/socmint/release_status_ui_routes_v12_10_18.py",
        "src/socmint/release_status_v12_10_19.py",
        "scripts/release_dashboard_decision_gate_v12_10_19.py",
        "release/V12_10_19_RELEASE_DASHBOARD_DECISION_ENGINE.md",
    ]
    files = {item: (Path(root) / item).exists() for item in required}
    checks = {
        "version_manifest_match": bool(
            manifest.get("exists") and manifest.get("version") == VERSION
        ),
        "required_files_present": all(files.values()),
        "report_available": gates.get("report_count", 0) > 0,
        "latest_pass_gate_available": gates.get("latest_release_gate_pass") is not None,
        "runtime_ready": bool(split_runtime.get("local_runtime_ready")),
    }
    blocking = {
        "version_manifest_match": checks["version_manifest_match"],
        "required_files_present": checks["required_files_present"],
        "latest_pass_gate_available": checks["latest_pass_gate_available"],
        "runtime_ready": checks["runtime_ready"],
    }
    ok = all(blocking.values())
    return {
        "schema": SCHEMA,
        "generated_at": utc_now(),
        "status": "pass" if ok else "needs_review",
        "decision": "GO" if ok else "HOLD",
        "version": version_payload(),
        "release": {
            "version": VERSION,
            "release_name": RELEASE_NAME,
            "release_channel": RELEASE_CHANNEL,
            "release_tag": RELEASE_TAG,
        },
        "manifest": manifest,
        "gates": gates,
        "tor": runtime,
        "runtime": runtime,
        "checks": checks,
        "blocking_checks": blocking,
        "sections": {
            "release_gate_health": "pass"
            if checks["latest_pass_gate_available"]
            else "needs_review",
            "runtime_reachability": "pass"
            if checks["runtime_ready"]
            else "needs_review",
            "file_visibility": "informational"
            if not runtime.get("file_visibility_ready")
            else "pass",
            "report_availability": "pass"
            if checks["report_available"]
            else "needs_review",
            "required_files": "pass"
            if checks["required_files_present"]
            else "needs_review",
        },
        "required_files": files,
    }
