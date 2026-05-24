from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA = "socmint.release_mount_contract.v12_10_20"
VERSION = "12.10.20"

REQUIRED_PATHS = [
    {
        "key": "release_manifest",
        "path": "release/CURRENT_STATUS.json",
        "kind": "file",
        "mount": "./release:/app/release:ro",
        "reason": "Release status needs the current release manifest.",
    },
    {
        "key": "release_markdown_reports",
        "path": "release",
        "kind": "glob",
        "pattern": "*.md",
        "mount": "./release:/app/release:ro",
        "reason": "Operator pages should see release documentation and reports.",
    },
    {
        "key": "decision_gate_script",
        "path": "scripts/release_dashboard_decision_gate_v12_10_19.py",
        "kind": "file",
        "mount": "./scripts:/app/scripts:ro",
        "reason": "The dashboard decision gate must be visible inside the app container.",
    },
    {
        "key": "gate_report_directory",
        "path": "var/socmint/rc_reports",
        "kind": "directory",
        "mount": "./var/socmint/rc_reports:/app/var/socmint/rc_reports",
        "reason": "Release status and gate viewer need runtime reports.",
    },
]


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _check_item(item: dict[str, str], root: str | Path = ".") -> dict[str, Any]:
    base = Path(root)
    path = base / item["path"]
    kind = item["kind"]
    exists = False
    detail: dict[str, Any] = {}

    if kind == "file":
        exists = path.is_file()
        detail["size_bytes"] = path.stat().st_size if exists else None
    elif kind == "directory":
        exists = path.is_dir()
        detail["entry_count"] = len(list(path.iterdir())) if exists else 0
    elif kind == "glob":
        pattern = item.get("pattern", "*")
        exists = path.is_dir() and any(path.glob(pattern))
        detail["matches"] = sorted(str(p) for p in path.glob(pattern))[:20] if path.is_dir() else []
    else:
        detail["error"] = f"unknown kind {kind}"

    return {
        **item,
        "absolute_path": str(path.resolve()) if path.exists() else str(path),
        "exists": exists,
        "status": "pass" if exists else "fail",
        "detail": detail,
        "fix": {
            "compose_service": "app",
            "add_volume": item["mount"],
            "compose_hint": f"Under services.app.volumes add: - {item['mount']}",
        },
    }


def docker_compose_patch_snippet(missing: list[dict[str, Any]]) -> str:
    mounts: list[str] = []
    for row in missing:
        mount = row.get("mount")
        if mount and mount not in mounts:
            mounts.append(mount)

    if not mounts:
        return "# No missing release-dashboard mounts detected."

    lines = [
        "# Add these under services.app.volumes in docker-compose.yml:",
        "services:",
        "  app:",
        "    volumes:",
    ]
    for mount in mounts:
        lines.append(f"      - {mount}")
    return "\n".join(lines)


def release_mount_contract(root: str | Path = ".") -> dict[str, Any]:
    rows = [_check_item(item, root) for item in REQUIRED_PATHS]
    missing = [row for row in rows if row["status"] != "pass"]
    status = "pass" if not missing else "fail"

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "generated_at": utc_now(),
        "status": status,
        "decision": "GO" if status == "pass" else "HOLD",
        "summary": {
            "required_count": len(rows),
            "pass_count": len(rows) - len(missing),
            "missing_count": len(missing),
        },
        "required_paths": rows,
        "missing": missing,
        "patch_guidance": docker_compose_patch_snippet(missing),
        "operator_command": "docker compose up -d --force-recreate app",
    }
