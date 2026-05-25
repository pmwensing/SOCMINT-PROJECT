#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from socmint.v12_10_54_runtime_guard import (
    VERSION,
    archive_integrity,
    rollback_instructions,
    runtime_schema_status,
    version_payload,
)


OUT_JSON = Path("release/v12_10_54/POST_RELEASE_RUNTIME_HARDENING_REPORT_V12_10_54.json")
OUT_MD = Path("release/v12_10_54/POST_RELEASE_RUNTIME_HARDENING_REPORT_V12_10_54.md")


def main() -> int:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)

    status = runtime_schema_status()
    archive = archive_integrity()
    version = version_payload()
    rollback = rollback_instructions()

    errors = []
    if not status["compatible"]:
        errors.extend(status["errors"])
    if not archive["integrity_ok"]:
        errors.extend(archive["errors"])

    result = {
        "version": VERSION,
        "runtime_status": status,
        "archive_integrity": archive,
        "version_payload": version,
        "rollback": rollback,
        "real_db_upgrade_blocked_by_default": True,
        "production_db_touched": False,
        "real_config_upgrade_run": False,
        "errors": errors,
        "release_status": "PASS GO" if not errors else "HOLD",
    }

    OUT_JSON.write_text(json.dumps(result, indent=2, sort_keys=True))
    write_md(result)

    print(json.dumps({
        "version": VERSION,
        "release_status": result["release_status"],
        "compatible": status["compatible"],
        "archive_integrity_ok": archive["integrity_ok"],
        "real_db_upgrade_blocked_by_default": True,
        "error_count": len(errors),
        "production_db_touched": False,
        "real_config_upgrade_run": False,
        "report_json": str(OUT_JSON),
        "report_md": str(OUT_MD),
    }, indent=2, sort_keys=True))

    return 0 if not errors else 1


def write_md(result):
    status = result["runtime_status"]
    archive = result["archive_integrity"]

    lines = [
        "# v12.10.54 Post-Release Runtime Hardening Report",
        "",
        f"- **release_status**: `{result['release_status']}`",
        f"- **runtime_schema_compatible**: `{status['compatible']}`",
        f"- **archive_integrity_ok**: `{archive['integrity_ok']}`",
        f"- **alembic_head**: `{status['live_alembic_head']}`",
        f"- **schema_lock**: `{status['schema_lock']}`",
        "- **real_db_upgrade_blocked_by_default**: `True`",
        "- **production_db_touched**: `False`",
        "- **real_config_upgrade_run**: `False`",
        "",
        "## Endpoints added",
        "",
        "- `/api/version`",
        "- `/api/schema/status`",
        "- `/api/schema/upgrade-guard`",
        "- `/api/release/archive-integrity`",
        "- `/api/schema/rollback/0018`",
        "",
        "## Errors",
        "",
    ]

    if result["errors"]:
        lines.extend(f"- {err}" for err in result["errors"])
    else:
        lines.append("- none")

    OUT_MD.write_text("\n".join(lines))


if __name__ == "__main__":
    raise SystemExit(main())
