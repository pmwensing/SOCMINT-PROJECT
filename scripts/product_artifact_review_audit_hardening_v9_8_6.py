from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(name: str, cmd: list[str], timeout: int = 240) -> dict:
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
        run("product-smoke", ["make", "product-smoke"]),
        run("product-artifact-review-smoke", ["make", "product-artifact-review-smoke"]),
        run(
            "product-artifact-review-audit-smoke-v9-8-6",
            [sys.executable, "scripts/product_artifact_review_audit_smoke_v9_8_6.py"],
        ),
    ]

    failed = [c for c in checks if not c["ok"]]
    status = "fail" if failed else "pass"

    report = {
        "status": status,
        "generated_at": now_iso(),
        "version": "9.8.6",
        "summary": f"{len(checks) - len(failed)}/{len(checks)} checks passed.",
        "checks": checks,
        "failed": [c["name"] for c in failed],
        "next_action": "Merge v9.8.6 into master"
        if status == "pass"
        else "Fix artifact audit failures before merge.",
    }

    json_path = Path("release/V9_8_6_ARTIFACT_REVIEW_AUDIT_HARDENING_REPORT.json")
    md_path = Path("release/V9_8_6_ARTIFACT_REVIEW_AUDIT_HARDENING_REPORT.md")
    storage_path = Path(
        "storage/product_qa/V9_8_6_ARTIFACT_REVIEW_AUDIT_HARDENING_REPORT.json"
    )

    json_path.write_text(json.dumps(report, indent=2))
    storage_path.write_text(json.dumps(report, indent=2))

    md = [
        "# v9.8.6 Artifact Review Audit Hardening Report",
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
