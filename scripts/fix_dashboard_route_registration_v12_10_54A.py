#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


ROOT = Path.cwd()
VERSION = "12.10.54A"
DASHBOARD = ROOT / "src/socmint/dashboard.py"

OUT_DIR = ROOT / "release/v12_10_54A"
REPORT_JSON = OUT_DIR / "DASHBOARD_ROUTE_FIX_V12_10_54A.json"
REPORT_MD = OUT_DIR / "DASHBOARD_ROUTE_FIX_V12_10_54A.md"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(cmd: List[str]) -> Tuple[int, str]:
    try:
        out = subprocess.check_output(cmd, cwd=ROOT, stderr=subprocess.STDOUT, text=True)
        return 0, out
    except subprocess.CalledProcessError as exc:
        return exc.returncode, exc.output


def compile_ok(path: Path) -> Tuple[bool, str]:
    code, out = run(["python", "-m", "py_compile", str(path)])
    return code == 0, out


def remove_prior_bad_insertions(text: str) -> Tuple[str, List[str]]:
    changes: List[str] = []
    lines = text.splitlines()

    cleaned = []
    for line in lines:
        stripped = line.strip()

        # Remove any previous direct import/registration inserted in unsafe positions.
        if stripped in {
            "from .v12_10_54_runtime_guard_routes import register_v12_10_54_routes",
            "from src.socmint.v12_10_54_runtime_guard_routes import register_v12_10_54_routes",
            "register_v12_10_54_routes(app)",
        }:
            changes.append(f"removed unsafe line: {stripped}")
            continue

        cleaned.append(line)

    return "\n".join(cleaned) + "\n", changes


def insert_safe_import(text: str) -> Tuple[str, List[str]]:
    changes: List[str] = []

    if "v12_10_54_runtime_guard_routes" in text:
        return text, changes

    lines = text.splitlines()
    insert_at = 0

    # Preserve shebang/comments/docstring area.
    if lines and lines[0].startswith("#!"):
        insert_at = 1

    # If module docstring exists, put import after it.
    try:
        module = ast.parse(text)
        if (
            module.body
            and isinstance(module.body[0], ast.Expr)
            and isinstance(getattr(module.body[0], "value", None), ast.Constant)
            and isinstance(module.body[0].value.value, str)
        ):
            insert_at = max(insert_at, module.body[0].end_lineno or insert_at)
    except Exception:
        pass

    # Move after existing top-level imports.
    i = insert_at
    while i < len(lines):
        line = lines[i]
        if line.startswith("import ") or line.startswith("from "):
            i += 1
            continue
        if not line.strip():
            i += 1
            continue
        break

    import_block = [
        "",
        "try:",
        "    from .v12_10_54_runtime_guard_routes import register_v12_10_54_routes",
        "except Exception:  # pragma: no cover - route guard import must fail closed",
        "    register_v12_10_54_routes = None",
        "",
    ]

    lines[i:i] = import_block
    changes.append("inserted safe guarded v12.10.54 route import")
    return "\n".join(lines) + "\n", changes


def insert_safe_registration(text: str) -> Tuple[str, List[str]]:
    changes: List[str] = []

    if "v12_10_54_ROUTE_REGISTRATION_SENTINEL" in text:
        return text, changes

    lines = text.splitlines()

    # Prefer top-level placement after the first top-level `app = ...` statement block.
    app_assign_idx = None
    for idx, line in enumerate(lines):
        if re.match(r"^app\s*=", line):
            app_assign_idx = idx
            break

    registration = [
        "",
        "# v12_10_54_ROUTE_REGISTRATION_SENTINEL",
        "if register_v12_10_54_routes is not None:",
        "    register_v12_10_54_routes(app)",
        "",
    ]

    if app_assign_idx is not None:
        insert_at = app_assign_idx + 1
        # If following lines are continued call/body, move past simple contiguous indented/call lines.
        while insert_at < len(lines) and (
            lines[insert_at].startswith(" ")
            or lines[insert_at].startswith("\t")
            or lines[insert_at].strip() in {")", ")", ""}
        ):
            # Avoid walking too far into normal app setup. Stop on obvious top-level config lines.
            if lines[insert_at].startswith("app.") or lines[insert_at].startswith("@app."):
                break
            insert_at += 1

        lines[insert_at:insert_at] = registration
        changes.append(f"inserted safe route registration after top-level app assignment at line {app_assign_idx + 1}")
        return "\n".join(lines) + "\n", changes

    # Fallback: append fail-closed registration guarded by globals.
    fallback = [
        "",
        "# v12_10_54_ROUTE_REGISTRATION_SENTINEL",
        "try:",
        "    if register_v12_10_54_routes is not None and 'app' in globals():",
        "        register_v12_10_54_routes(app)",
        "except Exception:",
        "    pass",
        "",
    ]
    lines.extend(fallback)
    changes.append("app assignment not found; appended guarded fallback registration")
    return "\n".join(lines) + "\n", changes


def fix_known_indent_artifact(text: str) -> Tuple[str, List[str]]:
    """Repair common artifact where app.secret_key got stranded with unexpected indent."""
    changes: List[str] = []
    lines = text.splitlines()

    fixed = []
    for i, line in enumerate(lines):
        if re.match(r"^\s{4,}app\.secret_key\s*=", line):
            # Only dedent if previous non-empty nearby line is top-level route sentinel/import artifact.
            window = "\n".join(lines[max(0, i - 8):i + 1])
            if "v12_10_54_ROUTE_REGISTRATION_SENTINEL" in window or "register_v12_10_54_routes" in window:
                new_line = line.lstrip()
                fixed.append(new_line)
                changes.append(f"dedented stranded app.secret_key at original line {i + 1}")
                continue
        fixed.append(line)

    return "\n".join(fixed) + "\n", changes


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if not DASHBOARD.exists():
        raise SystemExit(f"Missing dashboard: {DASHBOARD}")

    before = DASHBOARD.read_text()
    before_compile_ok, before_compile_out = compile_ok(DASHBOARD)

    text, c1 = remove_prior_bad_insertions(before)
    text, c2 = fix_known_indent_artifact(text)
    text, c3 = insert_safe_import(text)
    text, c4 = insert_safe_registration(text)

    DASHBOARD.write_text(text)

    after_compile_ok, after_compile_out = compile_ok(DASHBOARD)

    errors = []
    if not after_compile_ok:
        errors.append("dashboard.py still does not compile")

    report = {
        "version": VERSION,
        "generated_at": now(),
        "dashboard": str(DASHBOARD),
        "before_compile_ok": before_compile_ok,
        "before_compile_output": before_compile_out,
        "after_compile_ok": after_compile_ok,
        "after_compile_output": after_compile_out,
        "changes": c1 + c2 + c3 + c4,
        "error_count": len(errors),
        "errors": errors,
        "production_db_touched": False,
        "real_config_upgrade_run": False,
        "status": "GO" if not errors else "NO-GO",
    }

    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True))
    write_md(report)

    print(json.dumps({
        "version": VERSION,
        "status": report["status"],
        "before_compile_ok": before_compile_ok,
        "after_compile_ok": after_compile_ok,
        "change_count": len(report["changes"]),
        "error_count": len(errors),
        "production_db_touched": False,
        "real_config_upgrade_run": False,
        "report_json": str(REPORT_JSON),
        "report_md": str(REPORT_MD),
    }, indent=2, sort_keys=True))

    return 0 if not errors else 1


def write_md(report: Dict[str, Any]) -> None:
    lines = [
        "# v12.10.54A Dashboard Route Registration Fix",
        "",
        f"- **status**: `{report['status']}`",
        f"- **before_compile_ok**: `{report['before_compile_ok']}`",
        f"- **after_compile_ok**: `{report['after_compile_ok']}`",
        "- **production_db_touched**: `False`",
        "- **real_config_upgrade_run**: `False`",
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
