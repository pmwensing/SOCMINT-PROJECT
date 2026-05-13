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
    proc = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout, check=False)
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
        run("product-smoke", ["make", "product-smoke"]),
        run("artifact-review-smoke", ["make", "product-artifact-review-smoke"]),
        run("artifact-review-audit-smoke", ["make", "product-artifact-review-audit-smoke"]),
        run("export-manifest-smoke", ["make", "product-artifact-export-manifest-smoke"]),
        run("release-package-smoke", ["make", "product-release-package-smoke"]),
        run("zip-export-smoke", ["make", "product-release-package-zip-smoke"]),
        run("release-candidate-smoke-v9-9-0", [sys.executable, "scripts/product_release_candidate_smoke_v9_9_0.py"]),
    ]

    failed = [c for c in checks if not c["ok"]]
    status = "fail" if failed else "pass"

    report = {
        "status": status,
        "generated_at": now_iso(),
        "version": "9.9.0",
        "summary": f"{len(checks) - len(failed)}/{len(checks)} checks passed.",
        "checks": checks,
        "failed": [c["name"] for c in failed],
        "next_action": "Merge and tag v9.9.0 release candidate" if status == "pass" else "Fix release candidate failures before merge.",
    }

    json_path = Path("release/V9_9_0_RELEASE_CANDIDATE_HARDENING_REPORT.json")
    md_path = Path("release/V9_9_0_RELEASE_CANDIDATE_HARDENING_REPORT.md")
    storage_path = Path("storage/product_qa/V9_9_0_RELEASE_CANDIDATE_HARDENING_REPORT.json")

    json_path.write_text(json.dumps(report, indent=2))
    storage_path.write_text(json.dumps(report, indent=2))

    md = [
        "# v9.9.0 Release Candidate Hardening Report",
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
