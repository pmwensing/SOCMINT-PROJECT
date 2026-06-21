from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .version import (
    RELEASE_CHANNEL,
    RELEASE_NAME,
    RELEASE_TAG,
    VERSION,
    version_payload,
)

SCHEMA = "socmint.release_status.v12_10_17"
LATEST_GATE_SCHEMA = "socmint.release_gates.latest.v12_10_17"
DEFAULT_REPORT_ROOT = Path("var/socmint/rc_reports")


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _load_current_status(root: str | Path = ".") -> dict[str, Any]:
    path = Path(root) / "release" / "CURRENT_STATUS.json"
    if not path.exists():
        return {
            "exists": False,
            "path": str(path),
            "error": "missing release/CURRENT_STATUS.json",
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["exists"] = True
        payload["path"] = str(path)
        return payload
    except Exception as exc:
        return {"exists": True, "path": str(path), "error": str(exc)}


def _file_summary(path: Path) -> dict[str, Any]:
    try:
        stat = path.stat()
        payload: dict[str, Any] = {
            "path": str(path),
            "name": path.name,
            "exists": True,
            "size_bytes": stat.st_size,
            "modified_at_epoch": stat.st_mtime,
        }
        if path.suffix == ".json":
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                payload.update(
                    {
                        "schema": data.get("schema"),
                        "status": data.get("status"),
                        "decision": data.get("decision"),
                        "version": data.get("version"),
                        "generated_at": data.get("generated_at"),
                    }
                )
            except Exception as exc:
                payload["parse_error"] = str(exc)
        return payload
    except FileNotFoundError:
        return {"path": str(path), "name": path.name, "exists": False}


def latest_gate_reports(
    report_root: str | Path = DEFAULT_REPORT_ROOT,
) -> dict[str, Any]:
    root = Path(report_root)
    if not root.exists():
        return {
            "schema": LATEST_GATE_SCHEMA,
            "generated_at": utc_now(),
            "status": "missing_reports",
            "decision": "HOLD",
            "report_root": str(root),
            "reports": [],
            "latest": None,
        }
    candidates = sorted(
        [p for p in root.glob("*.json") if p.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    reports = [_file_summary(path) for path in candidates[:20]]
    latest = reports[0] if reports else None
    latest_status = latest.get("status") if latest else None
    latest_decision = latest.get("decision") if latest else None
    ok = latest_status == "pass" and latest_decision in {"GO", "PASS", None}
    return {
        "schema": LATEST_GATE_SCHEMA,
        "generated_at": utc_now(),
        "status": "pass" if ok else "needs_review" if latest else "missing_reports",
        "decision": "GO" if ok else "HOLD",
        "report_root": str(root),
        "latest": latest,
        "reports": reports,
        "report_count": len(candidates),
    }


def release_status(
    root: str | Path = ".", report_root: str | Path = DEFAULT_REPORT_ROOT
) -> dict[str, Any]:
    current = _load_current_status(root)
    gates = latest_gate_reports(report_root)
    version = version_payload()
    current_version = current.get("version")
    version_match = bool(current.get("exists") and current_version == VERSION)
    required_files = [
        "release/CURRENT_STATUS.json",
        "release/V12_10_17_MASTER_POST_MERGE_VERIFICATION.md",
        "scripts/post_merge_master_verify_v12_10_17.sh",
        "src/socmint/release_status_v12_10_17.py",
        "src/socmint/release_status_routes_v12_10_17.py",
    ]
    files = {path: (Path(root) / path).exists() for path in required_files}
    checks = {
        "version_manifest_match": version_match,
        "required_files_present": all(files.values()),
        "latest_gate_available": gates.get("latest") is not None,
        "latest_gate_passed": gates.get("status") == "pass",
    }
    status = "pass" if all(checks.values()) else "needs_review"
    return {
        "schema": SCHEMA,
        "generated_at": utc_now(),
        "status": status,
        "decision": "GO" if status == "pass" else "HOLD",
        "version": version,
        "release": {
            "version": VERSION,
            "release_name": RELEASE_NAME,
            "release_channel": RELEASE_CHANNEL,
            "release_tag": RELEASE_TAG,
        },
        "manifest": current,
        "gates": gates,
        "checks": checks,
        "required_files": files,
    }
