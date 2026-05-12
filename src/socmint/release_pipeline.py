from __future__ import annotations

from pathlib import Path
from typing import Any

RELEASE_PIPELINE_SCHEMA = "socmint.release_pipeline.v9_3_0"

REQUIRED_RELEASE_CHECKS = [
    "docker compose config",
    "alembic upgrade head",
    "backup restore smoke",
    "production boot smoke",
    "dependency audit",
    "hidden service hostname check",
    "direct public port exposure check",
]


def compose_file_status(root: str | Path = ".") -> dict[str, Any]:
    root_path = Path(root)
    candidates = [root_path / "docker-compose.yml", root_path / "docker-compose.yaml", root_path / "compose.yml", root_path / "compose.yaml"]
    found = [str(path) for path in candidates if path.exists()]
    return {
        "schema": RELEASE_PIPELINE_SCHEMA,
        "found": found,
        "present": bool(found),
    }


def release_pipeline_check(root: str | Path = ".") -> dict[str, Any]:
    compose = compose_file_status(root)
    scripts = {
        "production_smoke": Path(root, "scripts", "production_smoke.py").exists() or Path(root, "scripts", "production_smoke.sh").exists(),
        "backup_restore_smoke": Path(root, "scripts", "backup_restore_smoke.py").exists() or Path(root, "scripts", "backup_restore_smoke.sh").exists(),
        "test_script_directory": Path(root, "scripts").exists(),
    }
    checks = {
        "compose_file_present": compose["present"],
        "release_checks_declared": bool(REQUIRED_RELEASE_CHECKS),
        "script_directory_present": scripts["test_script_directory"],
        "production_smoke_known": scripts["production_smoke"],
        "backup_restore_smoke_known": scripts["backup_restore_smoke"],
    }
    return {
        "schema": RELEASE_PIPELINE_SCHEMA,
        "status": "ready" if all(checks.values()) else "needs_review",
        "checks": checks,
        "compose": compose,
        "scripts": scripts,
        "required_release_checks": REQUIRED_RELEASE_CHECKS,
    }


def release_pipeline_summary(root: str | Path = ".") -> dict[str, Any]:
    report = release_pipeline_check(root)
    return {
        "schema": RELEASE_PIPELINE_SCHEMA,
        "status": report["status"],
        "passed_checks": sum(1 for value in report["checks"].values() if value),
        "total_checks": len(report["checks"]),
        "required_release_checks": report["required_release_checks"],
    }


def release_workflow_spec() -> dict[str, Any]:
    return {
        "schema": RELEASE_PIPELINE_SCHEMA,
        "manual_release_steps": [
            "git checkout master && git pull",
            "docker compose config",
            "make ci",
            "make production-docker-smoke",
            "verify hidden service hostname exists when Tor profile is enabled",
            "verify direct public app port policy matches deployment profile",
            "run encrypted backup/restore drill",
            "capture production-release and security/hardening endpoint output",
        ],
        "artifacts": [
            "release readiness JSON",
            "production-release summary JSON",
            "gate enforcement summary JSON",
            "security checklist JSON",
            "backup restore smoke log",
        ],
    }
