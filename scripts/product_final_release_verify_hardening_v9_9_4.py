from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(name: str, cmd: list[str], timeout: int = 360) -> dict:
    print(f"[+] {name}: {' '.join(cmd)}")
    proc = subprocess.run(
        cmd, text=True, capture_output=True, timeout=timeout, check=False
    )
    ok = proc.returncode == 0
    print(("[PASS] " if ok else "[FAIL] ") + name)
    if not ok:
        if proc.stdout:
            print(proc.stdout[-4000:])
        if proc.stderr:
            print(proc.stderr[-4000:])
    return {
        "name": name,
        "ok": ok,
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-4000:],
    }


def main() -> int:
    Path("release").mkdir(exist_ok=True)
    Path("storage/product_qa").mkdir(parents=True, exist_ok=True)

    checks = [
        run("compileall-src", [sys.executable, "-m", "compileall", "src/socmint"]),
        run(
            "final-release-archive-smoke",
            ["make", "product-final-release-archive-smoke"],
        ),
        run(
            "final-release-verify-smoke-v9-9-4",
            [sys.executable, "scripts/product_final_release_verify_smoke_v9_9_4.py"],
        ),
    ]

    failed = [c for c in checks if not c["ok"]]
    status = "fail" if failed else "pass"

    report = {
        "status": status,
        "generated_at": now_iso(),
        "version": "9.9.4",
        "summary": f"{len(checks) - len(failed)}/{len(checks)} checks passed.",
        "checks": checks,
        "failed": [c["name"] for c in failed],
        "next_action": "Merge and tag v9.9.4 final release verification console"
        if status == "pass"
        else "Fix final release verification failures before merge.",
    }

    json_path = Path("release/V9_9_4_FINAL_RELEASE_VERIFY_HARDENING_REPORT.json")
    md_path = Path("release/V9_9_4_FINAL_RELEASE_VERIFY_HARDENING_REPORT.md")
    storage_path = Path(
        "storage/product_qa/V9_9_4_FINAL_RELEASE_VERIFY_HARDENING_REPORT.json"
    )

    json_path.write_text(json.dumps(report, indent=2))
    storage_path.write_text(json.dumps(report, indent=2))

    md = [
        "# v9.9.4 Final Release Verification Hardening Report",
        "",
        f"Generated: {report['generated_at']}",
        f"Status: **{report['status']}**",
        "",
        report["summary"],
        "",
        "## Failures",
        "",
        *([f"- {x}" for x in report["failed"]] or ["- None"]),
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
