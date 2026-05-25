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
VERSION = "12.10.37"

VALIDATION_REPORT = ROOT / "release/approved_draft_validation/APPROVED_DRAFT_STATIC_VALIDATION_V12_10_36.json"
DRAFT = ROOT / "release/approved_migration_draft/0018_APPROVED_MODEL_MIGRATION_DRAFT_V12_10_35.py"
def active_alembic_versions_dir() -> Path:
    cfg = configparser.ConfigParser()
    cfg.read(ROOT / "alembic.ini")
    script_location = cfg.get("alembic", "script_location", fallback="alembic")
    return ROOT / script_location / "versions"


PROMOTED = active_alembic_versions_dir() / "0018_approved_model_migration.py"

OUT_DIR = ROOT / "release/migration_promotion"
MANIFEST = OUT_DIR / "MIGRATION_PROMOTION_MANIFEST_V12_10_37.json"
REPORT_MD = OUT_DIR / "MIGRATION_PROMOTION_REPORT_V12_10_37.md"
REFUSAL_MD = OUT_DIR / "MIGRATION_PROMOTION_REFUSAL_V12_10_37.md"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(cmd: List[str]) -> Tuple[int, str]:
    try:
        out = subprocess.check_output(cmd, cwd=ROOT, stderr=subprocess.STDOUT, text=True)
        return 0, out
    except Exception as exc:
        return 1, getattr(exc, "output", repr(exc))


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"Missing required file: {path}")
    return json.loads(path.read_text())


def refuse(errors: List[str], context: Dict[str, Any] | None = None) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    payload = {
        "version": VERSION,
        "generated_at": utc_now(),
        "promotion_status": "REFUSED",
        "schema_mutation": "none",
        "alembic_upgrade_run": False,
        "promoted": False,
        "errors": errors,
        "context": context or {},
    }

    lines = [
        "# v12.10.37 Migration Promotion Refusal",
        "",
        "- **promotion_status**: `REFUSED`",
        "- **schema_mutation**: `none`",
        "- **alembic_upgrade_run**: `False`",
        "- **promoted**: `False`",
        "",
        "## Errors",
        "",
    ]

    for err in errors:
        lines.append(f"- {err}")

    REFUSAL_MD.write_text("\n".join(lines))
    MANIFEST.write_text(json.dumps(payload, indent=2, sort_keys=True))

    raise SystemExit("v12.10.37 promotion refused:\n- " + "\n- ".join(errors))


def sanitize_draft(text: str) -> str:
    text = text.replace("v12.10.35 APPROVED MIGRATION DRAFT — REVIEW BEFORE PROMOTION", "v12.10.37 APPROVED MODEL MIGRATION")
    text = text.replace("This file is generated outside alembic/versions.", "Promoted into alembic/versions by v12.10.37 promotion gate.")
    text = text.replace("It is not applied automatically.", "This migration is not applied automatically by this promotion gate.")
    text = text.replace("Promote only after human review of every TODO.", "TODO comments preserved for final schema review.")
    text = text.replace("# REVIEW DRAFT ONLY.", "# PROMOTED MIGRATION FILE — DO NOT UPGRADE WITHOUT FINAL DB SMOKE TEST.")
    text = text.replace("# Do not run until promoted in a later build.", "# Promoted by v12.10.37. No alembic upgrade was run by this build.")

    text = re.sub(
        r'revision\s*=\s*"0018_approved_model_migration"',
        'revision = "0018_approved_model_migration"',
        text,
    )
    text = re.sub(
        r'down_revision\s*=\s*"0017_v12_10_schema_reconciliation"',
        'down_revision = "0017_v12_10_schema_reconciliation"',
        text,
    )

    # Remove only "review draft" language; keep all TODO comments.
    forbidden_phrases = [
        'raise RuntimeError("NON-EXECUTABLE REVIEW DRAFT: do not run")',
        "NON-EXECUTABLE REVIEW DRAFT",
        "REVIEW ONLY — NOT A REAL MIGRATION",
    ]
    for phrase in forbidden_phrases:
        text = text.replace(phrase, "")

    return text


def parse_revision_fields(text: str) -> Dict[str, str | None]:
    rev = re.search(r'revision\s*=\s*[\'"]([^\'"]+)[\'"]', text)
    down = re.search(r'down_revision\s*=\s*[\'"]([^\'"]+)[\'"]', text)

    return {
        "revision": rev.group(1) if rev else None,
        "down_revision": down.group(1) if down else None,
    }


def validate_promoted_file(text: str, validation: Dict[str, Any]) -> List[str]:
    errors: List[str] = []

    fields = parse_revision_fields(text)
    if fields["revision"] != "0018_approved_model_migration":
        errors.append(f"promoted revision is wrong: {fields['revision']}")

    if fields["down_revision"] != "0017_v12_10_schema_reconciliation":
        errors.append(f"promoted down_revision is wrong: {fields['down_revision']}")

    if "op.create_table" not in text:
        errors.append("promoted migration has no op.create_table calls")

    if "op.drop_table" not in text:
        errors.append("promoted migration has no op.drop_table calls")

    if "TODO" not in text:
        errors.append("TODO comments were not preserved")

    approved_tables = validation.get("approved_tables", [])
    for table in approved_tables:
        if f'"{table}"' not in text and f"'{table}'" not in text:
            errors.append(f"approved table missing from promoted migration: {table}")

    if "RuntimeError" in text:
        errors.append("promoted migration still contains RuntimeError guard")

    return errors


def validate_alembic_head() -> Dict[str, Any]:
    code, out = run(["alembic", "heads"])
    heads = [line.split()[0] for line in out.splitlines() if line.strip()]

    return {
        "command_ok": code == 0,
        "raw": out,
        "heads": heads,
        "expected_head_present": "0018_approved_model_migration" in heads,
        "sole_head": heads == ["0018_approved_model_migration"],
    }


def promote() -> Dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    errors: List[str] = []

    if not VALIDATION_REPORT.exists():
        errors.append(f"missing v12.10.36 validation report: {VALIDATION_REPORT}")

    if not DRAFT.exists():
        errors.append(f"missing approved draft: {DRAFT}")

    if errors:
        refuse(errors)

    validation = load_json(VALIDATION_REPORT)

    if validation.get("promotion_status") != "GO":
        refuse(
            [f"v12.10.36 promotion_status is not GO: {validation.get('promotion_status')}"],
            {"validation_report": str(VALIDATION_REPORT), "validation": validation},
        )

    if validation.get("schema_mutation") != "none":
        refuse(["v12.10.36 validation report does not say schema_mutation=none"], validation)

    if validation.get("alembic_upgrade_run") is not False:
        refuse(["v12.10.36 validation report does not prove alembic_upgrade_run=false"], validation)

    draft_text = DRAFT.read_text()
    promoted_text = sanitize_draft(draft_text)

    pre_errors = validate_promoted_file(promoted_text, validation)
    if pre_errors:
        refuse(pre_errors, {"stage": "pre-write promoted validation"})

    PROMOTED.parent.mkdir(parents=True, exist_ok=True)
    PROMOTED.write_text(promoted_text)

    post_text = PROMOTED.read_text()
    post_errors = validate_promoted_file(post_text, validation)

    alembic = validate_alembic_head()
    if not alembic["command_ok"]:
        post_errors.append("alembic heads command failed")

    if not alembic["expected_head_present"]:
        post_errors.append("alembic does not see expected head 0018_approved_model_migration")

    if post_errors:
        refuse(post_errors, {"stage": "post-write promoted validation", "alembic": alembic})

    manifest = {
        "version": VERSION,
        "generated_at": utc_now(),
        "promotion_status": "PROMOTED",
        "schema_mutation": "none",
        "alembic_upgrade_run": False,
        "promoted": True,
        "source_draft": str(DRAFT),
        "promoted_path": str(PROMOTED),
        "active_alembic_versions_dir": str(active_alembic_versions_dir()),
        "validation_report": str(VALIDATION_REPORT),
        "approved_table_count": validation.get("approved_table_count"),
        "create_table_count": validation.get("create_table_count"),
        "drop_table_count": validation.get("drop_table_count"),
        "todo_count": validation.get("todo_count"),
        "alembic": alembic,
        "next_required_step": "Run a future DB smoke build before any alembic upgrade.",
    }

    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True))
    write_report(manifest)

    return manifest


def write_report(manifest: Dict[str, Any]) -> None:
    lines = [
        "# v12.10.37 Migration Promotion Report",
        "",
        f"- **promotion_status**: `{manifest['promotion_status']}`",
        "- **schema_mutation**: `none`",
        "- **alembic_upgrade_run**: `False`",
        f"- **promoted**: `{manifest['promoted']}`",
        f"- **promoted_path**: `{manifest['promoted_path']}`",
        f"- **approved_table_count**: `{manifest['approved_table_count']}`",
        f"- **create_table_count**: `{manifest['create_table_count']}`",
        f"- **drop_table_count**: `{manifest['drop_table_count']}`",
        f"- **todo_count**: `{manifest['todo_count']}`",
        "",
        "## Alembic head validation",
        "",
        f"- **command_ok**: `{manifest['alembic']['command_ok']}`",
        f"- **expected_head_present**: `{manifest['alembic']['expected_head_present']}`",
        f"- **sole_head**: `{manifest['alembic']['sole_head']}`",
        f"- **heads**: `{', '.join(manifest['alembic']['heads'])}`",
        "",
        "## Next required step",
        "",
        manifest["next_required_step"],
    ]

    REPORT_MD.write_text("\n".join(lines))


def main() -> int:
    manifest = promote()
    print(json.dumps({
        "version": VERSION,
        "promotion_status": manifest["promotion_status"],
        "schema_mutation": "none",
        "alembic_upgrade_run": False,
        "promoted": manifest["promoted"],
        "promoted_path": manifest["promoted_path"],
        "approved_table_count": manifest["approved_table_count"],
        "alembic_heads": manifest["alembic"]["heads"],
        "expected_head_present": manifest["alembic"]["expected_head_present"],
        "sole_head": manifest["alembic"]["sole_head"],
        "manifest": str(MANIFEST),
        "report": str(REPORT_MD),
    }, indent=2, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
