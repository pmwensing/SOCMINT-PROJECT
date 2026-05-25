#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from socmint.v12_10_54_runtime_guard import archive_integrity


OUT = Path("release/v12_10_54/ARCHIVE_INTEGRITY_V12_10_54.json")
OUT_MD = Path("release/v12_10_54/ARCHIVE_INTEGRITY_V12_10_54.md")


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    result = archive_integrity()
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True))

    lines = [
        "# v12.10.54 Release Archive Integrity",
        "",
        f"- **integrity_ok**: `{result['integrity_ok']}`",
        f"- **tarball_sha256**: `{result['tarball_sha256']}`",
        f"- **zip_sha256**: `{result['zip_sha256']}`",
        "- **production_db_touched**: `False`",
        "- **real_config_upgrade_run**: `False`",
        "",
        "## Errors",
        "",
    ]

    if result["errors"]:
        lines.extend(f"- {err}" for err in result["errors"])
    else:
        lines.append("- none")

    OUT_MD.write_text("\n".join(lines))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["integrity_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
