from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import socmint

RELEASE_INTEGRITY_SCHEMA = "socmint.release_integrity.v10_1_2"
EXPECTED_VERSION = "10.1.2"
REQUIRED_ROUTES = {
    "/api/v1/production-release/summary",
    "/api/v1/admin/certification/summary",
    "/api/v1/admin/operator-smoke/summary",
    "/api/v1/admin/beta/readiness/summary",
    "/api/v1/admin/security/checklist",
    "/api/v1/admin/gates/enforcement/summary",
    "/api/v1/admin/release-pipeline/summary",
    "/api/v1/beta/onboarding",
}
REQUIRED_RELEASE_NOTES = {
    "release/V10_1_1_VERSION_SYNC.md",
    "release/V10_1_2_RELEASE_INTEGRITY.md",
}


def pyproject_version(root: str | Path = ".") -> str | None:
    text = Path(root, "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"', text, re.MULTILINE)
    return match.group(1) if match else None


def route_registration_report(app) -> dict[str, Any]:
    routes = {rule.rule for rule in app.url_map.iter_rules()}
    missing = sorted(REQUIRED_ROUTES - routes)
    return {
        "schema": RELEASE_INTEGRITY_SCHEMA,
        "status": "pass" if not missing else "missing_routes",
        "required_count": len(REQUIRED_ROUTES),
        "missing_count": len(missing),
        "missing": missing,
        "registered_required_routes": sorted(REQUIRED_ROUTES & routes),
    }


def release_note_report(root: str | Path = ".") -> dict[str, Any]:
    root_path = Path(root)
    missing = sorted(path for path in REQUIRED_RELEASE_NOTES if not (root_path / path).exists())
    return {
        "schema": RELEASE_INTEGRITY_SCHEMA,
        "status": "pass" if not missing else "missing_release_notes",
        "required_count": len(REQUIRED_RELEASE_NOTES),
        "missing_count": len(missing),
        "missing": missing,
    }


def version_integrity_report(root: str | Path = ".") -> dict[str, Any]:
    pyproject = pyproject_version(root)
    package = getattr(socmint, "__version__", None)
    versions = {"pyproject": pyproject, "package": package, "expected": EXPECTED_VERSION}
    ok = pyproject == package == EXPECTED_VERSION
    return {
        "schema": RELEASE_INTEGRITY_SCHEMA,
        "status": "pass" if ok else "version_mismatch",
        "versions": versions,
    }


def release_integrity_report(app, root: str | Path = ".") -> dict[str, Any]:
    version = version_integrity_report(root)
    routes = route_registration_report(app)
    notes = release_note_report(root)
    checks = {
        "version_integrity": version["status"] == "pass",
        "route_registration": routes["status"] == "pass",
        "release_notes": notes["status"] == "pass",
    }
    return {
        "schema": RELEASE_INTEGRITY_SCHEMA,
        "status": "pass" if all(checks.values()) else "needs_review",
        "checks": checks,
        "version": version,
        "routes": routes,
        "release_notes": notes,
    }


def release_integrity_summary(app, root: str | Path = ".") -> dict[str, Any]:
    report = release_integrity_report(app, root)
    return {
        "schema": RELEASE_INTEGRITY_SCHEMA,
        "status": report["status"],
        "passed_checks": sum(1 for value in report["checks"].values() if value),
        "total_checks": len(report["checks"]),
        "missing_routes": report["routes"]["missing"],
        "missing_release_notes": report["release_notes"]["missing"],
        "versions": report["version"]["versions"],
    }
