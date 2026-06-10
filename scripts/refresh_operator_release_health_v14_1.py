#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


SCHEMA = "socmint.operator_release_health.v14_1"
DEFAULT_OUTPUT = Path("release/OPERATOR_RELEASE_HEALTH.json")


def _gh_json(args: list[str]) -> Any:
    result = subprocess.run(
        ["gh", *args],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "gh command failed")
    return json.loads(result.stdout or "null")


def build_release_health_snapshot() -> dict[str, Any]:
    open_prs = _gh_json(["pr", "list", "--state", "open", "--limit", "100", "--json", "number,title,headRefName,url"])
    runs = _gh_json(
        [
            "run",
            "list",
            "--branch",
            "master",
            "--limit",
            "10",
            "--json",
            "databaseId,workflowName,status,conclusion,headSha,url,createdAt",
        ]
    )
    latest_master = runs[0] if runs else None
    latest_sha = latest_master.get("headSha") if latest_master else None
    checks = [run for run in runs if run.get("headSha") == latest_sha] if latest_sha else []
    passing = all(check.get("conclusion") == "success" for check in checks)
    return {
        "schema": SCHEMA,
        "generated_at": datetime.now(UTC).isoformat(),
        "source": "gh",
        "open_pr_count": len(open_prs),
        "open_prs": open_prs,
        "latest_master": latest_master,
        "checks": checks,
        "status": "pass" if len(open_prs) == 0 and passing else "needs_review",
        "note": "generated from GitHub CLI release health query",
    }


def write_release_health_snapshot(path: str | Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    output = Path(path)
    payload = build_release_health_snapshot()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    payload = write_release_health_snapshot()
    print(json.dumps({"path": str(DEFAULT_OUTPUT), "status": payload["status"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
