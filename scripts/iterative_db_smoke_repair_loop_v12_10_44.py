#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


ROOT = Path.cwd()
VERSION = "12.10.44"

OUT_DIR = ROOT / "release/db_smoke_repair_loop"
REPORT_JSON = OUT_DIR / "ITERATIVE_DB_SMOKE_REPAIR_LOOP_V12_10_44.json"
REPORT_MD = OUT_DIR / "ITERATIVE_DB_SMOKE_REPAIR_LOOP_V12_10_44.md"

SMOKE_JSON = ROOT / "release/db_migration_smoke/DB_MIGRATION_SMOKE_V12_10_38.json"
GATE_JSON = ROOT / "release/db_smoke_gate/DB_SMOKE_RESULT_GATE_V12_10_39.json"
LOCATOR_JSON = ROOT / "release/db_smoke_exact_failure/DB_SMOKE_EXACT_FAILURE_LOCATOR_V12_10_42.json"

MAX_PASSES = 8


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
        return {}
    return json.loads(path.read_text())


def smoke_status() -> Dict[str, Any]:
    smoke = load_json(SMOKE_JSON)
    gate = load_json(GATE_JSON)
    locator = load_json(LOCATOR_JSON)

    return {
        "smoke_status": smoke.get("smoke_status"),
        "gate_release_status": gate.get("release_status"),
        "schema_lock": gate.get("schema_lock"),
        "production_db_touched": smoke.get("production_db_touched"),
        "real_config_upgrade_run": smoke.get("real_config_upgrade_run"),
        "approved_table_count": smoke.get("approved_table_count"),
        "missing_after_upgrade_count": len(smoke.get("missing_after_upgrade", [])) if smoke else None,
        "lingering_after_downgrade_count": len(smoke.get("lingering_after_downgrade", [])) if smoke else None,
        "version_after_upgrade": smoke.get("version_after_upgrade"),
        "version_after_downgrade": smoke.get("version_after_downgrade"),
        "probable_failing_table": locator.get("probable_failing_table"),
    }


def safety_assert(status: Dict[str, Any]) -> None:
    if status.get("production_db_touched") is True:
        raise SystemExit("SAFETY BLOCK: production_db_touched=True")
    if status.get("real_config_upgrade_run") is True:
        raise SystemExit("SAFETY BLOCK: real_config_upgrade_run=True")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    passes: List[Dict[str, Any]] = []

    # Baseline refresh.
    run(["python", "scripts/db_migration_smoke_v12_10_38.py"])
    run(["python", "scripts/db_smoke_result_gate_v12_10_39.py"])
    run(["python", "scripts/db_smoke_exact_failure_locator_v12_10_42.py"])

    baseline = smoke_status()
    safety_assert(baseline)

    if baseline.get("smoke_status") == "GO":
        final_status = "GO"
    else:
        final_status = "NO-GO"

        for idx in range(1, MAX_PASSES + 1):
            before = smoke_status()
            safety_assert(before)

            repair_code, repair_out = run(["python", "scripts/targeted_failed_table_smoke_repair_v12_10_43.py"])

            smoke_code, smoke_out = run(["python", "scripts/db_migration_smoke_v12_10_38.py"])
            gate_code, gate_out = run(["python", "scripts/db_smoke_result_gate_v12_10_39.py"])

            after_gate = smoke_status()
            safety_assert(after_gate)

            locator_code = 0
            locator_out = ""
            if after_gate.get("smoke_status") != "GO":
                locator_code, locator_out = run(["python", "scripts/db_smoke_exact_failure_locator_v12_10_42.py"])

            after = smoke_status()
            safety_assert(after)

            passes.append({
                "pass": idx,
                "before": before,
                "after": after,
                "repair_returncode": repair_code,
                "repair_output_tail": repair_out[-3000:],
                "smoke_returncode": smoke_code,
                "smoke_output_tail": smoke_out[-3000:],
                "gate_returncode": gate_code,
                "gate_output_tail": gate_out[-3000:],
                "locator_returncode": locator_code,
                "locator_output_tail": locator_out[-3000:],
            })

            if after.get("smoke_status") == "GO":
                final_status = "GO"
                break

            # If targeted repair did nothing useful and still same failure table, stop early.
            if (
                before.get("probable_failing_table")
                and before.get("probable_failing_table") == after.get("probable_failing_table")
                and repair_code != 0
            ):
                final_status = "NO-GO"
                break

    final = smoke_status()
    safety_assert(final)

    release_status = "PASS GO" if final.get("smoke_status") == "GO" else "HOLD"
    schema_lock = "DB_SMOKE_GO" if final.get("smoke_status") == "GO" else "DB_SMOKE_HOLD"

    report = {
        "version": VERSION,
        "generated_at": now(),
        "max_passes": MAX_PASSES,
        "pass_count": len(passes),
        "baseline": baseline,
        "passes": passes,
        "final": final,
        "final_status": final_status,
        "release_status": release_status,
        "schema_lock": schema_lock,
        "schema_mutation": "temp_sqlite_only",
        "production_db_touched": final.get("production_db_touched"),
        "real_config_upgrade_run": final.get("real_config_upgrade_run"),
        "next_action": "build v12.10.45 release readiness gate" if final.get("smoke_status") == "GO" else "manual repair required from latest v12.10.42 locator report",
    }

    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True))
    write_md(report)

    print(json.dumps({
        "version": VERSION,
        "final_status": final_status,
        "release_status": release_status,
        "schema_lock": schema_lock,
        "pass_count": len(passes),
        "smoke_status": final.get("smoke_status"),
        "probable_failing_table": final.get("probable_failing_table"),
        "missing_after_upgrade_count": final.get("missing_after_upgrade_count"),
        "lingering_after_downgrade_count": final.get("lingering_after_downgrade_count"),
        "production_db_touched": final.get("production_db_touched"),
        "real_config_upgrade_run": final.get("real_config_upgrade_run"),
        "report_json": str(REPORT_JSON),
        "report_md": str(REPORT_MD),
    }, indent=2, sort_keys=True))

    return 0 if final.get("smoke_status") == "GO" else 1


def write_md(report: Dict[str, Any]) -> None:
    final = report["final"]

    lines = [
        "# v12.10.44 Iterative DB Smoke Repair Loop",
        "",
        f"- **final_status**: `{report['final_status']}`",
        f"- **release_status**: `{report['release_status']}`",
        f"- **schema_lock**: `{report['schema_lock']}`",
        "- **schema_mutation**: `temp_sqlite_only`",
        f"- **production_db_touched**: `{report['production_db_touched']}`",
        f"- **real_config_upgrade_run**: `{report['real_config_upgrade_run']}`",
        f"- **pass_count**: `{report['pass_count']}`",
        f"- **smoke_status**: `{final.get('smoke_status')}`",
        f"- **probable_failing_table**: `{final.get('probable_failing_table')}`",
        f"- **missing_after_upgrade_count**: `{final.get('missing_after_upgrade_count')}`",
        f"- **lingering_after_downgrade_count**: `{final.get('lingering_after_downgrade_count')}`",
        f"- **version_after_upgrade**: `{final.get('version_after_upgrade')}`",
        f"- **version_after_downgrade**: `{final.get('version_after_downgrade')}`",
        f"- **next_action**: `{report['next_action']}`",
        "",
        "## Passes",
        "",
    ]

    if not report["passes"]:
        lines.append("- no repair passes required or baseline already GO")

    for p in report["passes"]:
        lines.extend([
            f"### Pass {p['pass']}",
            "",
            f"- before failing table: `{p['before'].get('probable_failing_table')}`",
            f"- after failing table: `{p['after'].get('probable_failing_table')}`",
            f"- before smoke: `{p['before'].get('smoke_status')}`",
            f"- after smoke: `{p['after'].get('smoke_status')}`",
            f"- repair_returncode: `{p['repair_returncode']}`",
            f"- smoke_returncode: `{p['smoke_returncode']}`",
            f"- gate_returncode: `{p['gate_returncode']}`",
            f"- locator_returncode: `{p['locator_returncode']}`",
            "",
        ])

    REPORT_MD.write_text("\n".join(lines))


if __name__ == "__main__":
    raise SystemExit(main())
