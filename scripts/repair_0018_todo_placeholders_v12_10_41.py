#!/usr/bin/env python3
from __future__ import annotations

import configparser
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


ROOT = Path.cwd()
VERSION = "12.10.41"

OUT_DIR = ROOT / "release" / "db_smoke_repair"
REPORT_JSON = OUT_DIR / "TODO_PLACEHOLDER_REPAIR_V12_10_41.json"
REPORT_MD = OUT_DIR / "TODO_PLACEHOLDER_REPAIR_V12_10_41.md"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(cmd: List[str]) -> Tuple[int, str]:
    try:
        out = subprocess.check_output(cmd, cwd=ROOT, stderr=subprocess.STDOUT, text=True)
        return 0, out
    except subprocess.CalledProcessError as exc:
        return exc.returncode, exc.output


def active_versions_dir() -> Path:
    cfg = configparser.ConfigParser()
    cfg.read(ROOT / "alembic.ini")
    script_location = cfg.get("alembic", "script_location", fallback="alembic")
    return ROOT / script_location / "versions"


def promoted_path() -> Path:
    return active_versions_dir() / "0018_approved_model_migration.py"


def replacement_for_todo_context(line: str) -> str:
    # Replace only executable TODO symbols/placeholders, not TODO comments.
    fixed = line

    replacements = {
        "length=255": "length=255",
        "sa.String(255)": "sa.String(255)",
        "String(255)": "String(255)",
        "sa.String(length=255)": "sa.String(length=255)",
        "String(length=255)": "String(length=255)",
        "nullable=TODO": "nullable=True",
        "default=TODO": "default=None",
        "server_default=TODO": "server_default=None",
        "index=TODO": "index=False",
        "unique=TODO": "unique=False",
    }

    for old, new in replacements.items():
        fixed = fixed.replace(old, new)

    # Bare TODO in argument position, for example: sa.Column("x", TODO)
    fixed = re.sub(r"(?<=,\s)TODO(?=\s*[,)\]])", "sa.String(255)", fixed)

    # Any remaining = TODO assignment inside function args.
    fixed = re.sub(r"=\s*TODO(?=\s*[,)\]])", "=None", fixed)

    return fixed


def repair_text(text: str) -> Tuple[str, List[Dict[str, Any]]]:
    changes: List[Dict[str, Any]] = []
    out_lines = []

    for idx, line in enumerate(text.splitlines(), 1):
        before_comment = line.split("#", 1)[0]
        fixed_line = line

        if "TODO" in before_comment:
            fixed_line = replacement_for_todo_context(line)

        if fixed_line != line:
            changes.append({
                "line": idx,
                "before": line,
                "after": fixed_line,
            })

        out_lines.append(fixed_line)

    return "\n".join(out_lines) + "\n", changes


def executable_todo_lines(text: str) -> List[Dict[str, Any]]:
    findings = []
    for idx, line in enumerate(text.splitlines(), 1):
        before_comment = line.split("#", 1)[0]
        if "TODO" in before_comment:
            findings.append({
                "line": idx,
                "text": line.rstrip(),
            })
    return findings


def patch_generator() -> List[Dict[str, Any]]:
    changes = []
    candidates = [
        ROOT / "scripts" / "build_approved_migration_draft_v12_10_35.py",
        ROOT / "scripts" / "promote_approved_migration_v12_10_37.py",
    ]

    for path in candidates:
        if not path.exists():
            continue

        text = path.read_text()
        fixed = text

        fixed = fixed.replace("sa.String(length=255)", "sa.String(length=255)")
        fixed = fixed.replace('return "sa.String(length=255)"', 'return "sa.String(length=255)"')
        fixed = fixed.replace("length=255", "length=255")

        if fixed != text:
            path.write_text(fixed)
            changes.append({
                "file": str(path),
                "change": "replaced executable TODO placeholders with safe defaults",
            })

    return changes


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    promoted = promoted_path()
    if not promoted.exists():
        raise SystemExit(f"Promoted migration missing: {promoted}")

    before = promoted.read_text()
    repaired, changes = repair_text(before)
    promoted.write_text(repaired)

    generator_changes = patch_generator()

    compile_code, compile_out = run(["python", "-m", "py_compile", str(promoted)])
    heads_code, heads_out = run(["alembic", "heads"])

    after = promoted.read_text()
    remaining_executable_todo = executable_todo_lines(after)

    errors = []
    if compile_code != 0:
        errors.append("promoted migration does not compile")

    if heads_code != 0:
        errors.append("alembic heads failed")

    if "0018_approved_model_migration" not in heads_out:
        errors.append("alembic does not see 0018_approved_model_migration head")

    if remaining_executable_todo:
        errors.append("executable TODO placeholders remain")

    report = {
        "version": VERSION,
        "generated_at": now(),
        "schema_mutation": "none",
        "production_db_touched": False,
        "real_config_upgrade_run": False,
        "promoted_migration": str(promoted),
        "changes": changes,
        "generator_changes": generator_changes,
        "remaining_executable_todo": remaining_executable_todo,
        "compile": {
            "returncode": compile_code,
            "output": compile_out,
        },
        "alembic_heads": {
            "returncode": heads_code,
            "output": heads_out,
        },
        "errors": errors,
        "repair_status": "GO" if not errors else "NO-GO",
    }

    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True))
    write_md(report)

    print(json.dumps({
        "version": VERSION,
        "repair_status": report["repair_status"],
        "schema_mutation": "none",
        "production_db_touched": False,
        "real_config_upgrade_run": False,
        "change_count": len(changes),
        "generator_change_count": len(generator_changes),
        "remaining_executable_todo_count": len(remaining_executable_todo),
        "compile_returncode": compile_code,
        "alembic_heads_returncode": heads_code,
        "report_json": str(REPORT_JSON),
        "report_md": str(REPORT_MD),
    }, indent=2, sort_keys=True))

    return 0 if not errors else 1


def write_md(report: Dict[str, Any]) -> None:
    lines = [
        "# v12.10.41 TODO Placeholder Repair Report",
        "",
        f"- **repair_status**: `{report['repair_status']}`",
        "- **schema_mutation**: `none`",
        "- **production_db_touched**: `False`",
        "- **real_config_upgrade_run**: `False`",
        f"- **promoted_migration**: `{report['promoted_migration']}`",
        f"- **change_count**: `{len(report['changes'])}`",
        f"- **generator_change_count**: `{len(report['generator_changes'])}`",
        f"- **remaining_executable_todo_count**: `{len(report['remaining_executable_todo'])}`",
        "",
        "## Errors",
        "",
    ]

    if report["errors"]:
        for err in report["errors"]:
            lines.append(f"- {err}")
    else:
        lines.append("- none")

    lines.extend(["", "## Migration changes", ""])

    if report["changes"]:
        for change in report["changes"][:200]:
            lines.append(f"### line {change['line']}")
            lines.append("")
            lines.append("Before:")
            lines.append("```python")
            lines.append(change["before"])
            lines.append("```")
            lines.append("After:")
            lines.append("```python")
            lines.append(change["after"])
            lines.append("```")
            lines.append("")
    else:
        lines.append("- no migration changes required")

    lines.extend(["", "## Generator changes", ""])

    if report["generator_changes"]:
        for change in report["generator_changes"]:
            lines.append(f"- `{change['file']}` — {change['change']}")
    else:
        lines.append("- none")

    REPORT_MD.write_text("\n".join(lines))


if __name__ == "__main__":
    raise SystemExit(main())
