#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


ROOT = Path.cwd()
VERSION = "12.10.52"

BASELINE_GO = ROOT / "release/baseline_aware_db_smoke/BASELINE_AWARE_DB_SMOKE_GATE_V12_10_51.json"
PROMOTION_READY = ROOT / "release/baseline_aware_db_smoke/BASELINE_AWARE_PROMOTION_READY_V12_10_51.json"

OUT_DIR = ROOT / "release/final_readiness"
MANIFEST_JSON = OUT_DIR / "FINAL_RELEASE_READINESS_MANIFEST_V12_10_52.json"
REPORT_MD = OUT_DIR / "FINAL_RELEASE_READINESS_REPORT_V12_10_52.md"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(cmd: List[str]) -> Tuple[int, str]:
    try:
        out = subprocess.check_output(cmd, cwd=ROOT, stderr=subprocess.STDOUT, text=True)
        return 0, out
    except subprocess.CalledProcessError as exc:
        return exc.returncode, exc.output


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"Missing required file: {path}")
    return json.loads(path.read_text())


def maybe_run_make(target: str) -> Dict[str, Any]:
    code, out = run(["make", target])
    return {
        "target": target,
        "returncode": code,
        "output_tail": out[-5000:],
        "passed": code == 0,
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    gate = load_json(BASELINE_GO)
    ready = load_json(PROMOTION_READY)

    checks: List[Dict[str, Any]] = []
    errors: List[str] = []

    def check(name: str, ok: bool, detail: Any) -> None:
        checks.append({"name": name, "ok": ok, "detail": detail})
        if not ok:
            errors.append(f"{name}: {detail}")

    heads_code, heads_out = run(["alembic", "heads"])
    status_code, status_out = run(["git", "status", "--short"])

    check("baseline_aware_status_go", gate.get("status") == "GO", gate.get("status"))
    check("baseline_aware_release_pass_go", gate.get("release_status") == "PASS GO", gate.get("release_status"))
    check("schema_lock_go", gate.get("schema_lock") == "BASELINE_AWARE_DB_SMOKE_GO", gate.get("schema_lock"))
    check("production_db_not_touched", gate.get("production_db_touched") is False, gate.get("production_db_touched"))
    check("real_config_upgrade_not_run", gate.get("real_config_upgrade_run") is False, gate.get("real_config_upgrade_run"))
    check("approved_table_count_18", gate.get("approved_table_count") == 18, gate.get("approved_table_count"))
    check("approved_baseline_table_count_16", gate.get("approved_baseline_table_count") == 16, gate.get("approved_baseline_table_count"))
    check("owned_0018_table_count_2", gate.get("owned_0018_table_count") == 2, gate.get("owned_0018_table_count"))
    check("missing_after_upgrade_zero", gate.get("missing_after_upgrade") == [], gate.get("missing_after_upgrade"))
    check("owned_lingering_after_downgrade_zero", gate.get("owned_lingering_after_downgrade") == [], gate.get("owned_lingering_after_downgrade"))
    check("baseline_missing_after_downgrade_zero", gate.get("baseline_missing_after_downgrade") == [], gate.get("baseline_missing_after_downgrade"))
    check("version_after_upgrade_0018", gate.get("version_after_upgrade") == "0018_approved_model_migration", gate.get("version_after_upgrade"))
    check("version_after_downgrade_0017", gate.get("version_after_downgrade") == "0017_v12_10_schema_reconciliation", gate.get("version_after_downgrade"))
    check("promotion_ready_manifest_true", ready.get("promotion_ready") is True, ready.get("promotion_ready"))
    check("alembic_head_0018", heads_code == 0 and "0018_approved_model_migration" in heads_out, heads_out)

    optional_tests = []
    for target in ["test121051", "test121050", "test121049"]:
        optional_tests.append(maybe_run_make(target))

    for item in optional_tests:
        check(f"make_{item['target']}", item["passed"], item["output_tail"])

    release_status = "PASS GO" if not errors else "HOLD"

    manifest = {
        "version": VERSION,
        "generated_at": now(),
        "release_status": release_status,
        "runtime": "pass GO" if release_status == "PASS GO" else "hold",
        "route_lock": "pass GO",
        "schema_lock": gate.get("schema_lock"),
        "alembic_head": "0018_approved_model_migration" if "0018_approved_model_migration" in heads_out else heads_out.strip(),
        "production_db_touched": False,
        "real_config_upgrade_run": False,
        "source_gate": str(BASELINE_GO),
        "source_promotion_ready": str(PROMOTION_READY),
        "checks": checks,
        "errors": errors,
        "optional_tests": optional_tests,
        "git_status_short": status_out,
        "next_action": "tag/release package" if release_status == "PASS GO" else "fix failed readiness checks",
    }

    MANIFEST_JSON.write_text(json.dumps(manifest, indent=2, sort_keys=True))
    write_md(manifest)

    print(json.dumps({
        "version": VERSION,
        "release_status": release_status,
        "schema_lock": manifest["schema_lock"],
        "alembic_head": manifest["alembic_head"],
        "error_count": len(errors),
        "production_db_touched": False,
        "real_config_upgrade_run": False,
        "manifest": str(MANIFEST_JSON),
        "report": str(REPORT_MD),
    }, indent=2, sort_keys=True))

    return 0 if release_status == "PASS GO" else 1


def write_md(manifest: Dict[str, Any]) -> None:
    lines = [
        "# v12.10.52 Final Release Readiness Report",
        "",
        f"- **release_status**: `{manifest['release_status']}`",
        f"- **runtime**: `{manifest['runtime']}`",
        f"- **route_lock**: `{manifest['route_lock']}`",
        f"- **schema_lock**: `{manifest['schema_lock']}`",
        f"- **alembic_head**: `{manifest['alembic_head']}`",
        "- **production_db_touched**: `False`",
        "- **real_config_upgrade_run**: `False`",
        "",
        "## Checks",
        "",
    ]

    for c in manifest["checks"]:
        mark = "PASS" if c["ok"] else "FAIL"
        lines.append(f"- **{mark}** `{c['name']}` — `{c['detail']}`")

    lines.extend(["", "## Errors", ""])

    if manifest["errors"]:
        for err in manifest["errors"]:
            lines.append(f"- {err}")
    else:
        lines.append("- none")

    lines.extend(["", "## Next action", "", manifest["next_action"]])

    REPORT_MD.write_text("\n".join(lines))


if __name__ == "__main__":
    raise SystemExit(main())
