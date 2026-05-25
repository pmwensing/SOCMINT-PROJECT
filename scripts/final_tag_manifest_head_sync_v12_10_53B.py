#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


ROOT = Path.cwd()
VERSION = "12.10.53B"

OUT_DIR = ROOT / "release/v12_10_53B"
REPORT_JSON = OUT_DIR / "FINAL_TAG_MANIFEST_HEAD_SYNC_V12_10_53B.json"
REPORT_MD = OUT_DIR / "FINAL_TAG_MANIFEST_HEAD_SYNC_V12_10_53B.md"

PKG_MANIFEST = ROOT / "release/v12_10_53/RELEASE_ARTIFACT_MANIFEST_V12_10_53.json"
TAG_MANIFEST_53 = ROOT / "release/v12_10_53/TAG_MANIFEST_V12_10_53.json"
TAG_READY_53A = ROOT / "release/v12_10_53A/TAG_READY_MANIFEST_V12_10_53A.json"

TARBALL = ROOT / "dist/SOCMINT-PROJECT-v12.10.53-release.tar.gz"
ZIPFILE = ROOT / "dist/SOCMINT-PROJECT-v12.10.53-release.zip"

EXPECTED_HEAD = "0018_approved_model_migration"
EXPECTED_SCHEMA_LOCK = "BASELINE_AWARE_DB_SMOKE_GO"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(cmd: List[str]) -> Tuple[int, str]:
    try:
        out = subprocess.check_output(cmd, cwd=ROOT, stderr=subprocess.STDOUT, text=True)
        return 0, out.strip()
    except subprocess.CalledProcessError as exc:
        return exc.returncode, exc.output.strip()


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"Missing required file: {path}")
    return json.loads(path.read_text())


def sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    before_code, before_head = run(["git", "rev-parse", "HEAD"])
    before_short_code, before_short = run(["git", "rev-parse", "--short", "HEAD"])

    package_code, package_out = run(["python", "scripts/release_package_tag_manifest_v12_10_53.py"])
    verify_code, verify_out = run(["python", "scripts/post_commit_package_refresh_v12_10_53A.py"])

    head_code, head = run(["git", "rev-parse", "HEAD"])
    short_code, short = run(["git", "rev-parse", "--short", "HEAD"])
    branch_code, branch = run(["git", "branch", "--show-current"])
    status_code, git_status = run(["git", "status", "--short"])
    heads_code, heads_out = run(["alembic", "heads"])

    pkg = load_json(PKG_MANIFEST)
    tag53 = load_json(TAG_MANIFEST_53)
    ready53a = load_json(TAG_READY_53A)

    tar_hash = sha256(TARBALL)
    zip_hash = sha256(ZIPFILE)

    checks: List[Dict[str, Any]] = []
    errors: List[str] = []
    warnings: List[str] = []

    def check(name: str, ok: bool, detail: Any, hard: bool = True) -> None:
        checks.append({"name": name, "ok": ok, "detail": detail, "hard": hard})
        if not ok and hard:
            errors.append(f"{name}: {detail}")
        elif not ok:
            warnings.append(f"{name}: {detail}")

    check("package_builder_passed", package_code == 0, package_out[-6000:])
    check("tag_ready_verifier_passed", verify_code == 0, verify_out[-6000:])
    check("package_release_status_pass_go", pkg.get("release_status") == "PASS GO", pkg.get("release_status"))
    check("tag_ready_release_status_pass_go", ready53a.get("release_status") == "PASS GO", ready53a.get("release_status"))
    check("tag_ready_true", ready53a.get("tag_ready") is True, ready53a.get("tag_ready"))
    check("package_manifest_commit_matches_head", pkg.get("full_commit") == head, {
        "pkg_full_commit": pkg.get("full_commit"),
        "head": head,
    })
    check("package_manifest_short_matches_head", pkg.get("commit") == short, {
        "pkg_commit": pkg.get("commit"),
        "head_short": short,
    })
    check("tag_manifest_commit_matches_head", tag53.get("commit") == head, {
        "tag_manifest_commit": tag53.get("commit"),
        "head": head,
    })
    check("tag_ready_manifest_current_head_matches_head", ready53a.get("current_head") == head, {
        "ready_current_head": ready53a.get("current_head"),
        "head": head,
    })
    check("tag_ready_manifest_commit_matches_head_short", ready53a.get("manifest_commit") == short, {
        "ready_manifest_commit": ready53a.get("manifest_commit"),
        "head_short": short,
    })
    check("live_alembic_head_0018", heads_code == 0 and EXPECTED_HEAD in heads_out, heads_out)
    check("schema_lock_go", pkg.get("schema_lock") == EXPECTED_SCHEMA_LOCK and ready53a.get("schema_lock") == EXPECTED_SCHEMA_LOCK, {
        "pkg_schema_lock": pkg.get("schema_lock"),
        "ready_schema_lock": ready53a.get("schema_lock"),
    })
    check("production_db_not_touched", pkg.get("production_db_touched") is False and ready53a.get("production_db_touched") is False, {
        "pkg": pkg.get("production_db_touched"),
        "ready": ready53a.get("production_db_touched"),
    })
    check("real_config_upgrade_not_run", pkg.get("real_config_upgrade_run") is False and ready53a.get("real_config_upgrade_run") is False, {
        "pkg": pkg.get("real_config_upgrade_run"),
        "ready": ready53a.get("real_config_upgrade_run"),
    })
    check("tarball_hash_matches_package_manifest", tar_hash == pkg.get("archives", {}).get("tarball", {}).get("sha256"), {
        "actual": tar_hash,
        "manifest": pkg.get("archives", {}).get("tarball", {}).get("sha256"),
    })
    check("zip_hash_matches_package_manifest", zip_hash == pkg.get("archives", {}).get("zip", {}).get("sha256"), {
        "actual": zip_hash,
        "manifest": pkg.get("archives", {}).get("zip", {}).get("sha256"),
    })

    expected_dirty_prefixes = (
        "release/v12_10_53/",
        "release/v12_10_53A/",
        "release/v12_10_53B/",
        "release/V12_10_53B_FINAL_TAG_MANIFEST_HEAD_SYNC.md",
        "dist/SOCMINT-PROJECT-v12.10.53-release.tar.gz",
        "dist/SOCMINT-PROJECT-v12.10.53-release.zip",
        "scripts/final_tag_manifest_head_sync_v12_10_53B.py",
        "scripts/test_v12_10_53B.sh",
        "tests/test_v12_10_53B_final_tag_manifest_head_sync.py",
        "Makefile",
        "pyproject.toml",
        "src/socmint/__init__.py",
    )
    unexpected_dirty = []
    for line in git_status.splitlines():
        if not line.strip():
            continue
        path = line[3:] if len(line) > 3 else line
        if not any(path.startswith(prefix) or path == prefix for prefix in expected_dirty_prefixes):
            unexpected_dirty.append(line)

    check("no_unexpected_dirty_files", not unexpected_dirty, unexpected_dirty, hard=False)

    final_tag_ready = len(errors) == 0

    report = {
        "version": VERSION,
        "generated_at": now(),
        "final_tag_ready": final_tag_ready,
        "release_status": "PASS GO" if final_tag_ready else "HOLD",
        "branch": branch,
        "before_head": before_head,
        "before_short": before_short,
        "head": head,
        "head_short": short,
        "package_manifest_commit": pkg.get("commit"),
        "package_manifest_full_commit": pkg.get("full_commit"),
        "tag_manifest_commit": tag53.get("commit"),
        "tag_ready_current_head": ready53a.get("current_head"),
        "alembic_head": EXPECTED_HEAD if EXPECTED_HEAD in heads_out else heads_out,
        "schema_lock": EXPECTED_SCHEMA_LOCK,
        "production_db_touched": False,
        "real_config_upgrade_run": False,
        "tarball": str(TARBALL),
        "tarball_sha256": tar_hash,
        "zip": str(ZIPFILE),
        "zip_sha256": zip_hash,
        "recommended_tag": "v12.10.53",
        "create_tag_command": "git tag -a v12.10.53 -m 'SOCMINT-PROJECT v12.10.53 release package'",
        "push_tag_command": "git push origin v12.10.53",
        "checks": checks,
        "errors": errors,
        "warnings": warnings,
        "git_status_short": git_status,
        "unexpected_dirty": unexpected_dirty,
        "next_action": "commit v12.10.53B refreshed manifests, rerun report121053B once, then create/push tag" if final_tag_ready else "fix hard blockers before tagging",
    }

    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True))
    write_md(report)

    print(json.dumps({
        "version": VERSION,
        "final_tag_ready": final_tag_ready,
        "release_status": report["release_status"],
        "head_short": short,
        "package_manifest_commit": pkg.get("commit"),
        "tag_ready_current_head": ready53a.get("current_head"),
        "alembic_head": report["alembic_head"],
        "schema_lock": report["schema_lock"],
        "error_count": len(errors),
        "warning_count": len(warnings),
        "tarball_sha256": tar_hash,
        "zip_sha256": zip_hash,
        "production_db_touched": False,
        "real_config_upgrade_run": False,
        "report_json": str(REPORT_JSON),
        "report_md": str(REPORT_MD),
    }, indent=2, sort_keys=True))

    return 0 if final_tag_ready else 1


def write_md(report: Dict[str, Any]) -> None:
    lines = [
        "# v12.10.53B Final Tag Manifest HEAD Sync",
        "",
        f"- **final_tag_ready**: `{report['final_tag_ready']}`",
        f"- **release_status**: `{report['release_status']}`",
        f"- **branch**: `{report['branch']}`",
        f"- **head_short**: `{report['head_short']}`",
        f"- **package_manifest_commit**: `{report['package_manifest_commit']}`",
        f"- **alembic_head**: `{report['alembic_head']}`",
        f"- **schema_lock**: `{report['schema_lock']}`",
        "- **production_db_touched**: `False`",
        "- **real_config_upgrade_run**: `False`",
        f"- **tarball_sha256**: `{report['tarball_sha256']}`",
        f"- **zip_sha256**: `{report['zip_sha256']}`",
        "",
        "## Checks",
        "",
    ]

    for check in report["checks"]:
        mark = "PASS" if check["ok"] else ("WARN" if not check["hard"] else "FAIL")
        lines.append(f"- **{mark}** `{check['name']}` — `{check['detail']}`")

    lines.extend(["", "## Errors", ""])

    if report["errors"]:
        for err in report["errors"]:
            lines.append(f"- {err}")
    else:
        lines.append("- none")

    lines.extend(["", "## Warnings", ""])

    if report["warnings"]:
        for warning in report["warnings"]:
            lines.append(f"- {warning}")
    else:
        lines.append("- none")

    lines.extend([
        "",
        "## Tag commands",
        "",
        "Do not run these until after committing v12.10.53B refreshed outputs and confirming report121053B still passes.",
        "",
        "```bash",
        report["create_tag_command"],
        report["push_tag_command"],
        "```",
        "",
        "## Next action",
        "",
        report["next_action"],
    ])

    REPORT_MD.write_text("\n".join(lines))


if __name__ == "__main__":
    raise SystemExit(main())
