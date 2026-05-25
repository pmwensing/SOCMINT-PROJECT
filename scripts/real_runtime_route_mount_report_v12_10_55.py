#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


OUT_DIR = Path("release/v12_10_55")
OUT_JSON = OUT_DIR / "REAL_RUNTIME_ROUTE_MOUNT_REPORT_V12_10_55.json"
OUT_MD = OUT_DIR / "REAL_RUNTIME_ROUTE_MOUNT_REPORT_V12_10_55.md"
ROUTE_MAP = OUT_DIR / "REAL_RUNTIME_ROUTE_MAP_V12_10_55.txt"


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    from src.socmint.v12_10_55_runtime_mount import runtime_mount_status

    result = runtime_mount_status()
    result["generated_at"] = datetime.now(timezone.utc).isoformat()

    OUT_JSON.write_text(json.dumps(result, indent=2, sort_keys=True))

    ROUTE_MAP.write_text("\n".join(result["verification"]["route_map"]) + "\n")
    write_md(result)

    print(json.dumps({
        "version": "12.10.55",
        "status": result["status"],
        "selected_runtime": result["selected_runtime"],
        "verification_mode": result["verification_mode"],
        "route_count": result["route_count"],
        "v12_10_54_route_count": len(result["v12_10_54_routes"]),
        "error_count": len(result["verification"]["errors"]),
        "production_db_touched": False,
        "real_config_upgrade_run": False,
        "report_json": str(OUT_JSON),
        "report_md": str(OUT_MD),
        "route_map": str(ROUTE_MAP),
    }, indent=2, sort_keys=True))

    return 0 if result["status"] == "GO" else 1


def write_md(result):
    lines = [
        "# v12.10.55 Real Runtime Route Mount Report",
        "",
        f"- **status**: `{result['status']}`",
        f"- **selected_runtime**: `{result['selected_runtime']}`",
        f"- **verification_mode**: `{result['verification_mode']}`",
        f"- **route_count**: `{result['route_count']}`",
        f"- **v12_10_54_route_count**: `{len(result['v12_10_54_routes'])}`",
        "- **production_db_touched**: `False`",
        "- **real_config_upgrade_run**: `False`",
        "",
        "## v12.10.54 routes mounted",
        "",
    ]

    for route in result["v12_10_54_routes"]:
        lines.append(f"- `{route}`")

    lines.extend(["", "## Endpoint verification", ""])

    for path, data in result["verification"]["endpoint_results"].items():
        lines.append(f"- `{path}`: `{data['status_code']}`")

    lines.extend(["", "## Errors", ""])

    if result["verification"]["errors"]:
        for err in result["verification"]["errors"]:
            lines.append(f"- {err}")
    else:
        lines.append("- none")

    lines.extend(["", "## Discovery attempts", ""])

    for attempt in result["discovery_attempts"]:
        lines.append(
            f"- `{attempt.get('module')}:{attempt.get('name')}` "
            f"{attempt.get('kind')} ok={attempt.get('ok')} error={attempt.get('error')}"
        )

    OUT_MD.write_text("\n".join(lines))


if __name__ == "__main__":
    raise SystemExit(main())
