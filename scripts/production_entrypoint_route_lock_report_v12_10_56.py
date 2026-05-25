#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


OUT_DIR = Path("release/v12_10_56")
OUT_JSON = OUT_DIR / "PRODUCTION_ENTRYPOINT_ROUTE_LOCK_V12_10_56.json"
OUT_MD = OUT_DIR / "PRODUCTION_ENTRYPOINT_ROUTE_LOCK_V12_10_56.md"
ROUTE_MAP = OUT_DIR / "PRODUCTION_ENTRYPOINT_ROUTE_MAP_V12_10_56.txt"


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    from src.socmint.v12_10_56_production_entrypoint import production_entrypoint_status

    result = production_entrypoint_status()
    result["generated_at"] = datetime.now(timezone.utc).isoformat()

    OUT_JSON.write_text(json.dumps(result, indent=2, sort_keys=True))

    routes = []
    if result.get("selected_verification"):
        routes = result["selected_verification"]["route_map"]
    ROUTE_MAP.write_text("\n".join(routes) + "\n")

    write_md(result)

    print(json.dumps({
        "version": "12.10.56A",
        "status": result["status"],
        "verification_mode": result["verification_mode"],
        "selected_spec": result["selected_spec"],
        "selected_wsgi_mode": result.get("selected_wsgi_mode"),
        "selected_wsgi_source": result.get("selected_wsgi_source"),
        "attempt_count": len(result["attempts"]),
        "route_count": len(routes),
        "v12_10_54_route_count": len(result.get("selected_verification", {}).get("v12_10_54_routes", [])) if result.get("selected_verification") else 0,
        "error_count": len(result["errors"]),
        "warning_count": len(result.get("warnings", [])),
        "production_db_touched": False,
        "real_config_upgrade_run": False,
        "report_json": str(OUT_JSON),
        "report_md": str(OUT_MD),
        "route_map": str(ROUTE_MAP),
    }, indent=2, sort_keys=True))

    return 0 if result["status"] == "GO" else 1


def write_md(result):
    lines = [
        "# v12.10.56A Production Entrypoint Route Lock",
        "",
        f"- **status**: `{result['status']}`",
        f"- **verification_mode**: `{result['verification_mode']}`",
        f"- **selected_spec**: `{result['selected_spec']}`",
        f"- **selected_wsgi_mode**: `{result.get('selected_wsgi_mode')}`",
        f"- **selected_wsgi_source**: `{result.get('selected_wsgi_source')}`",
        "- **production_db_touched**: `False`",
        "- **real_config_upgrade_run**: `False`",
        "",
        "## Selected v12.10.54 routes",
        "",
    ]

    selected = result.get("selected_verification") or {}
    for route in selected.get("v12_10_54_routes", []):
        lines.append(f"- `{route}`")

    lines.extend(["", "## Endpoint results", ""])
    for path, data in selected.get("endpoint_results", {}).items():
        lines.append(f"- `{path}`: `{data['status_code']}`")

    lines.extend(["", "## Errors", ""])
    if result["errors"]:
        lines.extend(f"- {err}" for err in result["errors"])
    else:
        lines.append("- none")

    lines.extend(["", "## Warnings", ""])
    if result.get("warnings"):
        lines.extend(f"- {w}" for w in result["warnings"])
    else:
        lines.append("- none")

    lines.extend(["", "## Entrypoint attempts", ""])
    for attempt in result["attempts"]:
        lines.append(
            f"- `{attempt['spec']}` loaded={attempt['loaded']} "
            f"verification_ok={attempt.get('verification_ok')} "
            f"wsgi_mode={attempt.get('wsgi_mode')} "
            f"source={attempt.get('wsgi_source')} "
            f"error={attempt.get('error')}"
        )

    lines.extend(["", "## Runtime lines", ""])
    for file_hit in result["discovery"]["files"]:
        lines.append(f"### `{file_hit['file']}`")
        if file_hit["runtime_lines"]:
            for line in file_hit["runtime_lines"]:
                lines.append(f"- `{line}`")
        else:
            lines.append("- no runtime command lines detected")

    OUT_MD.write_text("\n".join(lines))


if __name__ == "__main__":
    raise SystemExit(main())
