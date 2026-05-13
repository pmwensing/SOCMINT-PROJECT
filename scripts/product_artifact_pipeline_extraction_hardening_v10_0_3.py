from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(name: str, cmd: list[str], timeout: int = 720) -> dict:
    print(f"[+] {name}: {' '.join(cmd)}")
    proc = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout, check=False)
    ok = proc.returncode == 0
    print(("[PASS] " if ok else "[FAIL] ") + name)
    if not ok:
        if proc.stdout:
            print(proc.stdout[-6000:])
        if proc.stderr:
            print(proc.stderr[-6000:])
    return {
        "name": name,
        "ok": ok,
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-6000:],
        "stderr_tail": proc.stderr[-6000:],
    }


def main() -> int:
    Path("release").mkdir(exist_ok=True)
    Path("storage/product_qa").mkdir(parents=True, exist_ok=True)

    checks = [
        run("compileall-src", [sys.executable, "-m", "compileall", "src/socmint"]),
        run("post-release-extraction-smoke", ["make", "product-post-release-extraction-smoke"]),
        run("artifact-pipeline-extraction-smoke-v10-0-3", [sys.executable, "scripts/product_artifact_pipeline_extraction_smoke_v10_0_3.py"]),
    ]

    failed = [check for check in checks if not check["ok"]]
    status = "fail" if failed else "pass"

    report = {
        "status": status,
        "generated_at": now_iso(),
        "version": "10.0.3",
        "summary": f"{len(checks) - len(failed)}/{len(checks)} checks passed.",
        "checks": checks,
        "failed": [check["name"] for check in failed],
        "next_action": "Merge and tag v10.0.3 artifact pipeline split" if status == "pass" else "Fix v10.0.3 artifact pipeline extraction failures before merge.",
    }

    json_path = Path("release/V10_0_3_ARTIFACT_PIPELINE_EXTRACTION_HARDENING_REPORT.json")
    md_path = Path("release/V10_0_3_ARTIFACT_PIPELINE_EXTRACTION_HARDENING_REPORT.md")
    storage_path = Path("storage/product_qa/V10_0_3_ARTIFACT_PIPELINE_EXTRACTION_HARDENING_REPORT.json")

    json_path.write_text(json.dumps(report, indent=2))
    storage_path.write_text(json.dumps(report, indent=2))

    md = [
        "# v10.0.3 Product Artifact Pipeline Extraction Hardening Report",
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
