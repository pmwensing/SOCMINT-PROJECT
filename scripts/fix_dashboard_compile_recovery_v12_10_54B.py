#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


ROOT = Path.cwd()
VERSION = "12.10.54B"
DASHBOARD = ROOT / "src/socmint/dashboard.py"

OUT_DIR = ROOT / "release/v12_10_54B"
REPORT_JSON = OUT_DIR / "DASHBOARD_COMPILE_RECOVERY_V12_10_54B.json"
REPORT_MD = OUT_DIR / "DASHBOARD_COMPILE_RECOVERY_V12_10_54B.md"
CONTEXT_TXT = OUT_DIR / "DASHBOARD_COMPILE_ERROR_CONTEXT_V12_10_54B.txt"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(cmd: List[str]) -> Tuple[int, str]:
    try:
        out = subprocess.check_output(cmd, cwd=ROOT, stderr=subprocess.STDOUT, text=True)
        return 0, out
    except subprocess.CalledProcessError as exc:
        return exc.returncode, exc.output


def compile_dashboard() -> Tuple[bool, str]:
    code, out = run(["python", "-m", "py_compile", str(DASHBOARD)])
    return code == 0, out


def extract_error_line(output: str) -> int | None:
    m = re.search(r'File ".*dashboard\.py", line (\d+)', output)
    if not m:
        return None
    return int(m.group(1))


def context_around(text: str, line_no: int | None, radius: int = 25) -> str:
    lines = text.splitlines()
    if not line_no:
        start = max(0, len(lines) - 80)
        end = len(lines)
    else:
        start = max(0, line_no - radius - 1)
        end = min(len(lines), line_no + radius)

    out = []
    for idx in range(start, end):
        out.append(f"{idx + 1:05d}: {lines[idx]}")
    return "\n".join(out)


def remove_v12_10_54_artifacts(text: str) -> Tuple[str, List[str]]:
    changes: List[str] = []
    lines = text.splitlines()
    new: List[str] = []

    skip_block = False
    skip_indent = None

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Remove direct import lines and old guarded import block.
        if "v12_10_54_runtime_guard_routes" in line:
            changes.append(f"removed v12_10_54 import artifact at line {i + 1}: {stripped}")
            i += 1
            continue

        if stripped == "register_v12_10_54_routes(app)":
            changes.append(f"removed direct route registration at line {i + 1}")
            i += 1
            continue

        if "v12_10_54_ROUTE_REGISTRATION_SENTINEL" in line:
            changes.append(f"removed route registration sentinel block starting line {i + 1}")
            # Skip sentinel plus following if/try block until next top-level nonblank/nonindented line after consuming block.
            i += 1
            while i < len(lines):
                nxt = lines[i]
                if nxt.strip() == "":
                    i += 1
                    continue
                if nxt.startswith(" ") or nxt.startswith("\t") or nxt.lstrip().startswith(("if ", "try:", "except ", "pass")):
                    i += 1
                    continue
                break
            continue

        # Remove route registration guard remnants.
        if stripped in {
            "if register_v12_10_54_routes is not None:",
            "if register_v12_10_54_routes is not None and 'app' in globals():",
        }:
            changes.append(f"removed route guard block at line {i + 1}: {stripped}")
            i += 1
            while i < len(lines):
                nxt = lines[i]
                if nxt.strip() == "":
                    i += 1
                    continue
                if nxt.startswith(" ") or nxt.startswith("\t"):
                    i += 1
                    continue
                break
            continue

        new.append(line)
        i += 1

    return "\n".join(new) + "\n", changes


def repair_stranded_app_secret_key(text: str) -> Tuple[str, List[str]]:
    changes: List[str] = []
    lines = text.splitlines()
    new = []

    for idx, line in enumerate(lines):
        if re.match(r"^\s+app\.secret_key\s*=", line):
            # If previous nearby top-level app setup appears broken, dedent it.
            stripped = line.lstrip()
            new.append(stripped)
            changes.append(f"dedented app.secret_key at line {idx + 1}")
            continue
        new.append(line)

    return "\n".join(new) + "\n", changes


def add_safe_route_hook_to_bottom(text: str) -> Tuple[str, List[str]]:
    changes: List[str] = []

    if "V12_10_54_SAFE_ROUTE_HOOK" in text:
        return text, changes

    hook = r'''

# V12_10_54_SAFE_ROUTE_HOOK
def _register_v12_10_54_runtime_guard_routes_safe():
    """Register v12.10.54 runtime guard routes without affecting app startup."""
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
    changes.append("appended bottom-safe v12.10.54 route hook")
    return text.rstrip() + hook + "\n", changes


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    before_text = DASHBOARD.read_text()
    before_ok, before_out = compile_dashboard()
    before_line = extract_error_line(before_out)
    before_context = context_around(before_text, before_line)
    CONTEXT_TXT.write_text("BEFORE COMPILE OUTPUT\n=====================\n" + before_out + "\n\nCONTEXT\n=======\n" + before_context + "\n")

    text, c1 = remove_v12_10_54_artifacts(before_text)
    DASHBOARD.write_text(text)

    mid_ok, mid_out = compile_dashboard()

    c2: List[str] = []
    if not mid_ok:
        text, c2 = repair_stranded_app_secret_key(DASHBOARD.read_text())
        DASHBOARD.write_text(text)
        mid_ok, mid_out = compile_dashboard()

    c3: List[str] = []
    if mid_ok:
        text, c3 = add_safe_route_hook_to_bottom(DASHBOARD.read_text())
        DASHBOARD.write_text(text)

    after_ok, after_out = compile_dashboard()
    after_line = extract_error_line(after_out)
    after_context = context_around(DASHBOARD.read_text(), after_line)

    with CONTEXT_TXT.open("a") as f:
        f.write("\n\nAFTER COMPILE OUTPUT\n====================\n")
        f.write(after_out)
        f.write("\n\nAFTER CONTEXT\n=============\n")
        f.write(after_context)
        f.write("\n")

    errors = []
    if not after_ok:
        errors.append("dashboard.py still does not compile")

    report = {
        "version": VERSION,
        "generated_at": now(),
        "status": "GO" if not errors else "NO-GO",
        "before_compile_ok": before_ok,
        "mid_compile_ok": mid_ok,
        "after_compile_ok": after_ok,
        "before_compile_output": before_out,
        "mid_compile_output": mid_out,
        "after_compile_output": after_out,
        "before_error_line": before_line,
        "after_error_line": after_line,
        "changes": c1 + c2 + c3,
        "context_file": str(CONTEXT_TXT),
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
        "mid_compile_ok": mid_ok,
        "after_compile_ok": after_ok,
        "before_error_line": before_line,
        "after_error_line": after_line,
        "change_count": len(report["changes"]),
        "error_count": len(errors),
        "production_db_touched": False,
        "real_config_upgrade_run": False,
        "report_json": str(REPORT_JSON),
        "report_md": str(REPORT_MD),
        "context_file": str(CONTEXT_TXT),
    }, indent=2, sort_keys=True))

    return 0 if not errors else 1


def write_md(report: Dict[str, Any]) -> None:
    lines = [
        "# v12.10.54B Dashboard Compile Recovery",
        "",
        f"- **status**: `{report['status']}`",
        f"- **before_compile_ok**: `{report['before_compile_ok']}`",
        f"- **mid_compile_ok**: `{report['mid_compile_ok']}`",
        f"- **after_compile_ok**: `{report['after_compile_ok']}`",
        f"- **before_error_line**: `{report['before_error_line']}`",
        f"- **after_error_line**: `{report['after_error_line']}`",
        "- **production_db_touched**: `False`",
        "- **real_config_upgrade_run**: `False`",
        f"- **context_file**: `{report['context_file']}`",
        "",
        "## Changes",
        "",
    ]

    if report["changes"]:
        for c in report["changes"]:
            lines.append(f"- {c}")
    else:
        lines.append("- none")

    lines.extend(["", "## Errors", ""])

    if report["errors"]:
        for err in report["errors"]:
            lines.append(f"- {err}")
    else:
        lines.append("- none")

    REPORT_MD.write_text("\n".join(lines))


if __name__ == "__main__":
    raise SystemExit(main())
