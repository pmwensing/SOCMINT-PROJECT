from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(name: str, cmd: list[str], required: bool = True, timeout: int = 180) -> dict:
    print(f"[+] {name}")
    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout, check=False)
        ok = proc.returncode == 0
        print(("[PASS] " if ok else "[FAIL] ") + name)
        return {
            "name": name,
            "required": required,
            "ok": ok,
            "returncode": proc.returncode,
            "stdout_tail": proc.stdout[-3000:],
            "stderr_tail": proc.stderr[-3000:],
        }
    except Exception as exc:
        print(f"[ERROR] {name}: {exc}")
        return {"name": name, "required": required, "ok": False, "returncode": -1, "stdout_tail": "", "stderr_tail": str(exc)}


def file_check(path: str, required: bool = True) -> dict:
    ok = Path(path).exists()
    print(("[PASS] " if ok else "[FAIL] ") + f"file {path}")
    return {"name": f"file:{path}", "required": required, "ok": ok, "returncode": 0 if ok else 1, "stdout_tail": "", "stderr_tail": ""}


def main() -> int:
    Path("release").mkdir(exist_ok=True)
    Path("storage/product_qa").mkdir(parents=True, exist_ok=True)

    checks = [
        file_check("src/socmint/product_control_center.py"),
        file_check("src/socmint/dossier_quality_gate.py"),
        file_check("src/socmint/dossier_traceability.py"),
        file_check("src/socmint/ultimate_dossier.py", required=False),
        file_check("src/socmint/entity_dossier_v2.py", required=False),
        file_check("src/socmint/dossier_export.py", required=False),
        run("compileall-src", [sys.executable, "-m", "compileall", "src/socmint"]),
        run("product-control-import", [sys.executable, "-c", "from src.socmint.product_control_center import build_status, release_readiness; print(build_status()['version']); print(release_readiness()['status'])"]),
        run("quality-gate-import", [sys.executable, "-c", "from src.socmint.dossier_quality_gate import dossier_quality_gate; print(dossier_quality_gate('demo-subject')['status'])"]),
        run("traceability-import", [sys.executable, "-c", "from src.socmint.dossier_traceability import evidence_to_dossier_traceability; print(evidence_to_dossier_traceability('demo-subject')['status'])"]),
    ]

    if Path("scripts/ultimate_dossier_smoke_v7_8_0.py").exists():
        checks.append(run("ultimate-dossier-smoke", ["env", "PYTHONPATH=src", sys.executable, "scripts/ultimate_dossier_smoke_v7_8_0.py"], required=False))

    required_failed = [c for c in checks if c["required"] and not c["ok"]]
    optional_failed = [c for c in checks if not c["required"] and not c["ok"]]

    status = "fail" if required_failed else "warn" if optional_failed else "pass"

    report = {
        "status": status,
        "summary": f"{len(checks) - len(required_failed) - len(optional_failed)}/{len(checks)} checks passed; {len(required_failed)} required failed; {len(optional_failed)} optional failed.",
        "generated_at": now_iso(),
        "version": "9.7.4",
        "checks": checks,
        "required_failed": [c["name"] for c in required_failed],
        "optional_failed": [c["name"] for c in optional_failed],
        "next_action": "Cut v9.8 Productized Release" if status == "pass" else "Fix failed checks before v9.8.",
    }

    Path("storage/product_qa/V9_7_4_PRODUCT_QA_REPORT.json").write_text(json.dumps(report, indent=2))
    Path("release/V9_7_PRODUCT_SMOKE_REPORT.json").write_text(json.dumps(report, indent=2))

    md = [
        "# v9.7.4 Product Smoke Report",
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
        "## Optional Failures",
        "",
        *([f"- {x}" for x in report["optional_failed"]] or ["- None"]),
        "",
        "## Next Action",
        "",
        report["next_action"],
        "",
    ]
    Path("release/V9_7_PRODUCT_SMOKE_REPORT.md").write_text("\n".join(md))

    print(json.dumps({"status": status, "report": "release/V9_7_PRODUCT_SMOKE_REPORT.md"}, indent=2))
    return 0 if status in {"pass", "warn"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
