from __future__ import annotations

import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PRODUCT_VERSION = "9.7.4"
PRODUCT_NAME = "SOCMINT Workbench Product Build Suite"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_cmd(args: list[str], timeout: int = 20) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            args, text=True, capture_output=True, timeout=timeout, check=False
        )
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
        }
    except Exception as exc:
        return {"ok": False, "returncode": -1, "stdout": "", "stderr": str(exc)}


def exists(path: str) -> bool:
    return Path(path).exists()


def git_state() -> dict[str, Any]:
    return {
        "branch": run_cmd(["git", "branch", "--show-current"])["stdout"],
        "commit": run_cmd(["git", "rev-parse", "--short", "HEAD"])["stdout"],
        "status_short": run_cmd(["git", "status", "--short"])["stdout"],
    }


def system_health() -> dict[str, Any]:
    required = {
        "product_control_center": "src/socmint/product_control_center.py",
        "dossier_quality_gate": "src/socmint/dossier_quality_gate.py",
        "dossier_traceability": "src/socmint/dossier_traceability.py",
        "product_qa_script": "scripts/product_qa_v9_7_4.py",
    }
    optional = {
        "dossier_export": "src/socmint/dossier_export.py",
        "entity_dossier_v2": "src/socmint/entity_dossier_v2.py",
        "ultimate_dossier": "src/socmint/ultimate_dossier.py",
        "v7_8_smoke": "scripts/test_v7_8_0.sh",
        "ultimate_dossier_smoke": "scripts/ultimate_dossier_smoke_v7_8_0.py",
    }

    required_status = {k: exists(v) for k, v in required.items()}
    optional_status = {k: exists(v) for k, v in optional.items()}

    missing_required = [k for k, ok in required_status.items() if not ok]
    missing_optional = [k for k, ok in optional_status.items() if not ok]

    status = "pass"
    if missing_required:
        status = "fail"
    elif missing_optional:
        status = "warn"

    return {
        "status": status,
        "generated_at": now_iso(),
        "version": PRODUCT_VERSION,
        "python": platform.python_version(),
        "required": required_status,
        "optional": optional_status,
        "missing_required": missing_required,
        "missing_optional": missing_optional,
    }


def smoke_summary() -> dict[str, Any]:
    path = Path("release/V9_7_PRODUCT_SMOKE_REPORT.json")
    if not path.exists():
        return {
            "status": "not_run",
            "message": "Run make product-smoke.",
            "last_report": None,
        }
    try:
        data = json.loads(path.read_text())
    except Exception as exc:
        return {"status": "error", "message": str(exc), "last_report": str(path)}
    return {
        "status": data.get("status", "unknown"),
        "message": data.get("summary", ""),
        "last_report": str(path),
        "checks": data.get("checks", []),
    }


def build_status() -> dict[str, Any]:
    return {
        "product": PRODUCT_NAME,
        "version": PRODUCT_VERSION,
        "generated_at": now_iso(),
        "git": git_state(),
        "health": system_health(),
        "smoke": smoke_summary(),
    }


def release_readiness() -> dict[str, Any]:
    status = build_status()
    blockers: list[str] = []
    warnings: list[str] = []

    health = status["health"]
    smoke = status["smoke"]

    if health["status"] == "fail":
        blockers.extend(health["missing_required"])
    if health["status"] == "warn":
        warnings.extend(health["missing_optional"])

    if smoke["status"] != "pass":
        blockers.append("product_smoke_not_passing")

    if status["git"]["status_short"]:
        warnings.append("git_worktree_has_local_changes")

    result = (
        "pass" if not blockers and not warnings else "warn" if not blockers else "fail"
    )

    return {
        "status": result,
        "generated_at": now_iso(),
        "version": PRODUCT_VERSION,
        "blockers": blockers,
        "warnings": warnings,
        "recommended_next_action": "Cut v9.8 Productized Release"
        if result == "pass"
        else "Resolve blockers/warnings before v9.8.",
        "build_status": status,
    }


def write_product_reports() -> dict[str, str]:
    Path("release").mkdir(exist_ok=True)

    build = build_status()
    ready = release_readiness()

    build_path = Path("release/V9_7_1_PRODUCT_BUILD_STATUS.json")
    ready_path = Path("release/V9_7_1_RELEASE_READINESS.json")
    md_path = Path("release/V9_7_1_PRODUCT_BUILD_CONTROL_CENTER.md")

    build_path.write_text(json.dumps(build, indent=2))
    ready_path.write_text(json.dumps(ready, indent=2))

    md = [
        "# v9.7.1 Product Build Control Center",
        "",
        f"Generated: {now_iso()}",
        f"Status: **{ready['status']}**",
        "",
        "## Blockers",
        "",
        *([f"- {x}" for x in ready["blockers"]] or ["- None"]),
        "",
        "## Warnings",
        "",
        *([f"- {x}" for x in ready["warnings"]] or ["- None"]),
        "",
        "## Next Action",
        "",
        ready["recommended_next_action"],
        "",
    ]
    md_path.write_text("\n".join(md))

    return {
        "build_status_json": str(build_path),
        "release_readiness_json": str(ready_path),
        "control_center_md": str(md_path),
    }
