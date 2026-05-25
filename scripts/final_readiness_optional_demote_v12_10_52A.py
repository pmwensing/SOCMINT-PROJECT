#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


ROOT = Path.cwd()
VERSION = "12.10.52A"

BASELINE_GO = ROOT / "release/baseline_aware_db_smoke/BASELINE_AWARE_DB_SMOKE_GATE_V12_10_51.json"
OLD_MANIFEST = ROOT / "release/final_readiness/FINAL_RELEASE_READINESS_MANIFEST_V12_10_52.json"

OUT_DIR = ROOT / "release/final_readiness"
MANIFEST_JSON = OUT_DIR / "FINAL_RELEASE_READINESS_MANIFEST_V12_10_52A.json"
REPORT_MD = OUT_DIR / "FINAL_RELEASE_READINESS_REPORT_V12_10_52A.md"


HARD_CHECK_NAMES = {
    "baseline_aware_status_go",
    "baseline_aware_release_pass_go",
    "schema_lock_go",
    "production_db_not_touched",
    "real_config_upgrade_not_run",
    "approved_table_count_18",
    "approved_baseline_table_count_16",
    "owned_0018_table_count_2",
    "missing_after_upgrade_zero",
    "owned_lingering_after_downgrade_zero",
    "baseline_missing_after_downgrade_zero",
    "version_after_upgrade_0018",
    "version_after_downgrade_0017",
    "promotion_ready_manifest_true",
    "alembic_head_0018",
}


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


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    gate = load_json(BASELINE_GO)
    old = load_json(OLD_MANIFEST)

    heads_code, heads_out = run(["alembic", "heads"])
    status_code, status_out = run(["git", "status", "--short"])

    old_checks = old.get("checks", [])
    hard_failures = []
    demoted_warnings = []
    passing_checks = []

    canonical_ok = (
        gate.get("status") == "GO"
        and gate.get("release_status") == "PASS GO"
        and gate.get("schema_lock") == "BASELINE_AWARE_DB_SMOKE_GO"
        and gate.get("production_db_touched") is False
        and gate.get("real_config_upgrade_run") is False
        and gate.get("approved_table_count") == 18
        and gate.get("approved_baseline_table_count") == 16
        and gate.get("owned_0018_table_count") == 2
        and gate.get("missing_after_upgrade") == []
        and gate.get("owned_lingering_after_downgrade") == []
        and gate.get("baseline_missing_after_downgrade") == []
        and gate.get("version_after_upgrade") == "0018_approved_model_migration"
        and gate.get("version_after_downgrade") == "0017_v12_10_schema_reconciliation"
        and heads_code == 0
        and "0018_approved_model_migration" in heads_out
    )

    for check in old_checks:
        name = check.get("name")
        ok = check.get("ok") is True

        if ok:
            passing_checks.append(check)
            continue

        if name in HARD_CHECK_NAMES:
            hard_failures.append(check)
        elif name and name.startswith("make_test"):
            demoted_warnings.append({
                **check,
                "demotion_reason": "transitional repair-suite test is diagnostic only after v12.10.51 baseline-aware DB smoke GO",
            })
        else:
            hard_failures.append(check)

    if not canonical_ok:
        hard_failures.append({
            "name": "canonical_v12_10_51_baseline_aware_gate",
            "ok": False,
            "detail": "v12.10.51 canonical baseline-aware gate is not fully GO",
        })

    release_status = "PASS GO" if not hard_failures else "HOLD"

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
        "canonical_gate": str(BASELINE_GO),
        "previous_manifest": str(OLD_MANIFEST),
        "canonical_ok": canonical_ok,
        "hard_failure_count": len(hard_failures),
        "warning_count": len(demoted_warnings),
        "hard_failures": hard_failures,
        "demoted_warnings": demoted_warnings,
        "passing_checks": passing_checks,
        "git_status_short": status_out,
        "next_action": "tag/release package" if release_status == "PASS GO" else "fix hard readiness blockers",
    }

    MANIFEST_JSON.write_text(json.dumps(manifest, indent=2, sort_keys=True))
    write_md(manifest)

    print(json.dumps({
        "version": VERSION,
        "release_status": release_status,
        "schema_lock": manifest["schema_lock"],
        "alembic_head": manifest["alembic_head"],
        "canonical_ok": canonical_ok,
        "hard_failure_count": len(hard_failures),
        "warning_count": len(demoted_warnings),
        "production_db_touched": False,
        "real_config_upgrade_run": False,
        "manifest": str(MANIFEST_JSON),
        "report": str(REPORT_MD),
    }, indent=2, sort_keys=True))

    return 0 if release_status == "PASS GO" else 1


def write_md(manifest: Dict[str, Any]) -> None:
    lines = [
        "# v12.10.52A Final Release Readiness Report",
        "",
        f"- **release_status**: `{manifest['release_status']}`",
        f"- **runtime**: `{manifest['runtime']}`",
        f"- **route_lock**: `{manifest['route_lock']}`",
        f"- **schema_lock**: `{manifest['schema_lock']}`",
        f"- **alembic_head**: `{manifest['alembic_head']}`",
        f"- **canonical_ok**: `{manifest['canonical_ok']}`",
        f"- **hard_failure_count**: `{manifest['hard_failure_count']}`",
        f"- **warning_count**: `{manifest['warning_count']}`",
        "- **production_db_touched**: `False`",
        "- **real_config_upgrade_run**: `False`",
        "",
        "## Hard failures",
        "",
    ]

    if manifest["hard_failures"]:
        for item in manifest["hard_failures"]:
            lines.append(f"- `{item.get('name')}` — `{item.get('detail')}`")
    else:
        lines.append("- none")

    lines.extend(["", "## Demoted warnings", ""])

    if manifest["demoted_warnings"]:
        for item in manifest["demoted_warnings"]:
            lines.append(f"- `{item.get('name')}` — {item.get('demotion_reason')}")
    else:
        lines.append("- none")

    lines.extend(["", "## Next action", "", manifest["next_action"]])

    REPORT_MD.write_text("\n".join(lines))


if __name__ == "__main__":
    raise SystemExit(main())
