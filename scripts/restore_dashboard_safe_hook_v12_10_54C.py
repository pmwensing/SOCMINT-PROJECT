#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


ROOT = Path.cwd()
VERSION = "12.10.54C"

DASHBOARD = ROOT / "src/socmint/dashboard.py"
OUT_DIR = ROOT / "release/v12_10_54C"
REPORT_JSON = OUT_DIR / "RESTORE_DASHBOARD_SAFE_HOOK_V12_10_54C.json"
REPORT_MD = OUT_DIR / "RESTORE_DASHBOARD_SAFE_HOOK_V12_10_54C.md"
BROKEN_BACKUP = OUT_DIR / "dashboard_broken_before_restore_v12_10_54C.py"
COMPILE_CONTEXT = OUT_DIR / "dashboard_compile_context_v12_10_54C.txt"


SAFE_HOOK = r'''
# V12_10_54_SAFE_ROUTE_HOOK
def _register_v12_10_54_runtime_guard_routes_safe():
    """Register v12.10.54 runtime guard routes without running DB migration."""
    try:
        from .v12_10_54_runtime_guard_routes import register_v12_10_54_routes
    except Exception:
        return False

    try:
        register_v12_10_54_routes(app)
        return True
    except Exception:
        return False


_register_v12_10_54_runtime_guard_routes_safe()
'''


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(cmd: List[str]) -> Tuple[int, str]:
    try:
        out = subprocess.check_output(cmd, cwd=ROOT, stderr=subprocess.STDOUT, text=True)
        return 0, out
    except subprocess.CalledProcessError as exc:
        return exc.returncode, exc.output


def compile_file(path: Path) -> Tuple[bool, str]:
    code, out = run(["python", "-m", "py_compile", str(path)])
    return code == 0, out


def compile_context(text: str, output: str) -> str:
    m = re.search(r'File ".*dashboard\.py", line (\d+)', output)
    line_no = int(m.group(1)) if m else None
    lines = text.splitlines()

    if line_no:
        start = max(0, line_no - 25)
        end = min(len(lines), line_no + 25)
    else:
        start = 0
        end = min(len(lines), 80)

    context = []
    for idx in range(start, end):
        context.append(f"{idx + 1:05d}: {lines[idx]}")

    return "\n".join(context)


def git_restore_dashboard() -> Tuple[bool, str]:
    code, out = run(["git", "checkout", "--", str(DASHBOARD.relative_to(ROOT))])
    return code == 0, out


def strip_existing_v54_hook(text: str) -> str:
    marker = "# V12_10_54_SAFE_ROUTE_HOOK"
    if marker not in text:
        return text

    idx = text.index(marker)
    before = text[:idx].rstrip()
    return before + "\n"


def insert_hook_before_main(text: str) -> Tuple[str, str]:
    text = strip_existing_v54_hook(text).rstrip() + "\n"

    main_pattern = re.compile(r'(?m)^if\s+__name__\s*==\s*["\']__main__["\']\s*:\s*$')
    match = main_pattern.search(text)

    if match:
        insert_at = match.start()
        new_text = text[:insert_at].rstrip() + "\n\n" + SAFE_HOOK.strip() + "\n\n" + text[insert_at:]
        return new_text, "inserted hook before __main__ guard"

    return text.rstrip() + "\n\n" + SAFE_HOOK.strip() + "\n", "appended hook at EOF"


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if not DASHBOARD.exists():
        raise SystemExit(f"Missing dashboard: {DASHBOARD}")

    before_text = DASHBOARD.read_text()
    BROKEN_BACKUP.write_text(before_text)

    before_ok, before_compile = compile_file(DASHBOARD)
    COMPILE_CONTEXT.write_text(
        "BEFORE COMPILE\n==============\n"
        + before_compile
        + "\n\nBEFORE CONTEXT\n==============\n"
        + compile_context(before_text, before_compile)
        + "\n"
    )

    restored_ok, restored_output = git_restore_dashboard()
    restored_text = DASHBOARD.read_text()
    restored_compile_ok, restored_compile_out = compile_file(DASHBOARD)

    hook_mode = "not attempted"
    if restored_compile_ok:
        hooked_text, hook_mode = insert_hook_before_main(restored_text)
        DASHBOARD.write_text(hooked_text)

    after_text = DASHBOARD.read_text()
    after_ok, after_compile = compile_file(DASHBOARD)

    with COMPILE_CONTEXT.open("a") as f:
        f.write("\n\nAFTER COMPILE\n=============\n")
        f.write(after_compile)
        f.write("\n\nAFTER CONTEXT\n=============\n")
        f.write(compile_context(after_text, after_compile))
        f.write("\n")

    errors = []
    if not restored_ok:
        errors.append("git checkout -- dashboard.py failed")
    if not restored_compile_ok:
        errors.append("restored dashboard.py does not compile")
    if not after_ok:
        errors.append("dashboard.py does not compile after safe hook insertion")
    if "# V12_10_54_SAFE_ROUTE_HOOK" not in after_text:
        errors.append("safe hook marker missing after patch")

    report = {
        "version": VERSION,
        "generated_at": now(),
        "status": "GO" if not errors else "NO-GO",
        "dashboard": str(DASHBOARD),
        "broken_backup": str(BROKEN_BACKUP),
        "compile_context": str(COMPILE_CONTEXT),
        "before_compile_ok": before_ok,
        "before_compile_output": before_compile,
        "restored_ok": restored_ok,
        "restored_output": restored_output,
        "restored_compile_ok": restored_compile_ok,
        "restored_compile_output": restored_compile_out,
        "hook_mode": hook_mode,
        "after_compile_ok": after_ok,
        "after_compile_output": after_compile,
        "errors": errors,
        "production_db_touched": False,
        "real_config_upgrade_run": False,
    }

    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True))
    write_md(report)

    print(json.dumps({
        "version": VERSION,
        "status": report["status"],
        "before_compile_ok": before_ok,
        "restored_ok": restored_ok,
        "restored_compile_ok": restored_compile_ok,
        "hook_mode": hook_mode,
        "after_compile_ok": after_ok,
        "error_count": len(errors),
        "production_db_touched": False,
        "real_config_upgrade_run": False,
        "report_json": str(REPORT_JSON),
        "report_md": str(REPORT_MD),
        "broken_backup": str(BROKEN_BACKUP),
        "compile_context": str(COMPILE_CONTEXT),
    }, indent=2, sort_keys=True))

    return 0 if not errors else 1


def write_md(report: Dict[str, Any]) -> None:
    lines = [
        "# v12.10.54C Restore Dashboard + Safe Hook Report",
        "",
        f"- **status**: `{report['status']}`",
        f"- **before_compile_ok**: `{report['before_compile_ok']}`",
        f"- **restored_ok**: `{report['restored_ok']}`",
        f"- **restored_compile_ok**: `{report['restored_compile_ok']}`",
        f"- **hook_mode**: `{report['hook_mode']}`",
        f"- **after_compile_ok**: `{report['after_compile_ok']}`",
        "- **production_db_touched**: `False`",
        "- **real_config_upgrade_run**: `False`",
        f"- **broken_backup**: `{report['broken_backup']}`",
        f"- **compile_context**: `{report['compile_context']}`",
        "",
        "## Errors",
        "",
    ]

    if report["errors"]:
        for err in report["errors"]:
            lines.append(f"- {err}")
    else:
        lines.append("- none")

    REPORT_MD.write_text("\n".join(lines))


if __name__ == "__main__":
    raise SystemExit(main())
