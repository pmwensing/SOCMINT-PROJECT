from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(name: str, cmd: list[str], required: bool = True, timeout: int = 240) -> dict:
    print(f"[+] {name}: {' '.join(cmd)}")
    proc = subprocess.run(
        cmd, text=True, capture_output=True, timeout=timeout, check=False
    )
    ok = proc.returncode == 0
    print(("[PASS] " if ok else "[FAIL] ") + name)
    if not ok:
        if proc.stdout:
            print(proc.stdout[-3000:])
        if proc.stderr:
            print(proc.stderr[-3000:])
    return {
        "name": name,
        "required": required,
        "ok": ok,
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-3000:],
        "stderr_tail": proc.stderr[-3000:],
    }


def main() -> int:
    Path("release").mkdir(exist_ok=True)
    Path("storage/product_qa").mkdir(parents=True, exist_ok=True)

    checks = [
        run("compileall-src", [sys.executable, "-m", "compileall", "src/socmint"]),
        run("product-smoke-v9-7-4", ["make", "product-smoke"]),
        run(
            "product-route-smoke-v9-8-1",
            [sys.executable, "scripts/product_route_smoke_v9_8_1.py"],
        ),
    ]

    required_failed = [c for c in checks if c["required"] and not c["ok"]]
    status = "fail" if required_failed else "pass"

    report = {
        "status": status,
        "generated_at": now_iso(),
        "version": "9.8.1",
        "summary": f"{len(checks) - len(required_failed)}/{len(checks)} required checks passed.",
        "checks": checks,
        "required_failed": [c["name"] for c in required_failed],
        "next_action": "Merge v9.8.1 into master"
        if status == "pass"
        else "Fix route/hardening failures before merge.",
    }

    json_path = Path("release/V9_8_1_RELEASE_HARDENING_REPORT.json")
    md_path = Path("release/V9_8_1_RELEASE_HARDENING_REPORT.md")
    storage_path = Path("storage/product_qa/V9_8_1_RELEASE_HARDENING_REPORT.json")

    json_path.write_text(json.dumps(report, indent=2))
    storage_path.write_text(json.dumps(report, indent=2))

    md = [
        "# v9.8.1 Product Release Hardening Report",
        "",
        f"Generated: {report['generated_at']}",
        f"Status: **{report['status']}**",
        "",
        report["summary"],
        "",
        "## Required Failures",
        "",
        *([f"- {x}" for x in report["required_failed"]] or ["- None"]),
        "",
        "## Next Action",
        "",
        report["next_action"],
        "",
    ]
    md_path.write_text("\n".join(md))

    print(json.dumps({"status": status, "report": str(md_path)}, indent=2))
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
