from __future__ import annotations

from pathlib import Path
from typing import Any

PRODUCTION_INSTALLER_SCHEMA = "socmint.production_installer.v10_2_0"

REQUIRED_INSTALLER_FILES = {
    "installer": "scripts/install_production.sh",
    "env_example": ".env.production.example",
    "local_rebuild": "docs/LOCAL_REBUILD_V10_2.md",
    "deployment_pack": "docs/PRODUCTION_DEPLOYMENT_PACK.md",
}

INSTALLER_STEPS = [
    "verify system dependencies",
    "create production env file from template",
    "install python dependencies",
    "run database migrations",
    "create admin account",
    "run backup restore smoke",
    "run production boot smoke",
    "print local and deployment URLs",
]


def installer_file_status(root: str | Path = ".") -> dict[str, Any]:
    root_path = Path(root)
    files = {
        key: {"path": path, "present": (root_path / path).exists()}
        for key, path in REQUIRED_INSTALLER_FILES.items()
    }
    missing = [key for key, item in files.items() if not item["present"]]
    return {
        "schema": PRODUCTION_INSTALLER_SCHEMA,
        "status": "ready" if not missing else "missing_files",
        "files": files,
        "missing": missing,
    }


def installer_plan() -> dict[str, Any]:
    return {
        "schema": PRODUCTION_INSTALLER_SCHEMA,
        "steps": INSTALLER_STEPS,
        "outputs": [
            ".env.production",
            "database migrations applied",
            "admin bootstrap confirmation",
            "backup restore smoke result",
            "production boot smoke result",
        ],
    }


def installer_readiness_report(root: str | Path = ".") -> dict[str, Any]:
    files = installer_file_status(root)
    plan = installer_plan()
    checks = {
        "installer_files": files["status"] == "ready",
        "installer_steps_declared": bool(plan["steps"]),
        "installer_outputs_declared": bool(plan["outputs"]),
    }
    return {
        "schema": PRODUCTION_INSTALLER_SCHEMA,
        "status": "ready" if all(checks.values()) else "needs_review",
        "checks": checks,
        "files": files,
        "plan": plan,
    }


def installer_readiness_summary(root: str | Path = ".") -> dict[str, Any]:
    report = installer_readiness_report(root)
    return {
        "schema": PRODUCTION_INSTALLER_SCHEMA,
        "status": report["status"],
        "passed_checks": sum(1 for value in report["checks"].values() if value),
        "total_checks": len(report["checks"]),
        "missing_files": report["files"]["missing"],
    }
