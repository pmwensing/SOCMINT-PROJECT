#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple


VERSION = "12.10.54"
TAG = "v12.10.53"
OUT_JSON = Path("release/v12_10_54/TAG_VERIFICATION_REPORT_V12_10_54.json")
OUT_MD = Path("release/v12_10_54/TAG_VERIFICATION_REPORT_V12_10_54.md")


def run(cmd: List[str]) -> Tuple[int, str]:
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
        return 0, out.strip()
    except subprocess.CalledProcessError as exc:
        return exc.returncode, exc.output.strip()


def main() -> int:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)

    tag_code, tag_out = run(["git", "tag", "--list", TAG])
    show_code, show_out = run(["git", "show", "--stat", TAG])
    remote_code, remote_out = run(["git", "ls-remote", "--tags", "origin", TAG])

    tag_exists = tag_code == 0 and TAG in tag_out
    remote_exists = remote_code == 0 and TAG in remote_out

    warnings = []
    if not tag_exists:
        warnings.append("local tag not found")
    if not remote_exists:
        warnings.append("remote tag not found")

    result = {
        "version": VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tag": TAG,
        "tag_exists_local": tag_exists,
        "tag_exists_remote": remote_exists,
        "tag_show_returncode": show_code,
        "tag_show_tail": show_out[-6000:],
        "remote_returncode": remote_code,
        "remote_output": remote_out,
        "warnings": warnings,
        "production_db_touched": False,
        "real_config_upgrade_run": False,
    }

    OUT_JSON.write_text(json.dumps(result, indent=2, sort_keys=True))

    lines = [
        "# v12.10.54 Tag Verification Report",
        "",
        f"- **tag**: `{TAG}`",
        f"- **tag_exists_local**: `{tag_exists}`",
        f"- **tag_exists_remote**: `{remote_exists}`",
        "- **production_db_touched**: `False`",
        "- **real_config_upgrade_run**: `False`",
        "",
        "## Warnings",
        "",
    ]

    if warnings:
        lines.extend(f"- {w}" for w in warnings)
    else:
        lines.append("- none")

    OUT_MD.write_text("\n".join(lines))

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
