#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


ROOT = Path.cwd()
VERSION = "12.10.53A"

SOURCE_MANIFEST = ROOT / "release/v12_10_53/RELEASE_ARTIFACT_MANIFEST_V12_10_53.json"
SOURCE_TAG_MANIFEST = ROOT / "release/v12_10_53/TAG_MANIFEST_V12_10_53.json"

OUT_DIR = ROOT / "release/v12_10_53A"
TAG_READY_JSON = OUT_DIR / "TAG_READY_MANIFEST_V12_10_53A.json"
REPORT_MD = OUT_DIR / "POST_COMMIT_PACKAGE_REFRESH_REPORT_V12_10_53A.md"

EXPECTED_HEAD = "0018_approved_model_migration"
EXPECTED_SCHEMA_LOCK = "BASELINE_AWARE_DB_SMOKE_GO"

TARBALL = ROOT / "dist/SOCMINT-PROJECT-v12.10.53-release.tar.gz"
ZIPFILE = ROOT / "dist/SOCMINT-PROJECT-v12.10.53-release.zip"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(cmd: List[str]) -> Tuple[int, str]:
    try:
        out = subprocess.check_output(cmd, cwd=ROOT, stderr=subprocess.STDOUT, text=True)
        return 0, out.strip()
    except subprocess.CalledProcessError as exc:
        return exc.returncode, exc.output.strip()


def sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"Missing required file: {path}")
    return json.loads(path.read_text())


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    before_code, before_head = run(["git", "rev-parse", "HEAD"])
    before_short_code, before_short = run(["git", "rev-parse", "--short", "HEAD"])

    rerun_code, rerun_out = run(["python", "scripts/release_package_tag_manifest_v12_10_53.py"])

    head_code, current_head = run(["git", "rev-parse", "HEAD"])
    short_code, current_short = run(["git", "rev-parse", "--short", "HEAD"])
    branch_code, branch = run(["git", "branch", "--show-current"])
    status_code, git_status = run(["git", "status", "--short"])
    heads_code, heads_out = run(["alembic", "heads"])

    manifest = load_json(SOURCE_MANIFEST)
    tag_manifest = load_json(SOURCE_TAG_MANIFEST)

    tar_hash = sha256(TARBALL)
    zip_hash = sha256(ZIPFILE)

    errors: List[str] = []
    warnings: List[str] = []
    checks: List[Dict[str, Any]] = []

    def check(name: str, ok: bool, detail: Any, hard: bool = True) -> None:
        checks.append({"name": name, "ok": ok, "detail": detail, "hard": hard})
        if not ok and hard:
            errors.append(f"{name}: {detail}")
        elif not ok:
            warnings.append(f"{name}: {detail}")

    check("rerun_v12_10_53_builder_passed", rerun_code == 0, rerun_out[-6000:])
    check("manifest_release_status_pass_go", manifest.get("release_status") == "PASS GO", manifest.get("release_status"))
    check("manifest_schema_lock_go", manifest.get("schema_lock") == EXPECTED_SCHEMA_LOCK, manifest.get("schema_lock"))
    check("manifest_alembic_head_0018", EXPECTED_HEAD in str(manifest.get("alembic_head")), manifest.get("alembic_head"))
    check("live_alembic_head_0018", heads_code == 0 and EXPECTED_HEAD in heads_out, heads_out)
    check("manifest_commit_matches_current_head", manifest.get("full_commit") == current_head, {
        "manifest_full_commit": manifest.get("full_commit"),
        "current_head": current_head,
    })
    check("manifest_short_commit_matches_current_head", manifest.get("commit") == current_short, {
        "manifest_commit": manifest.get("commit"),
        "current_short": current_short,
    })
    check("tag_manifest_commit_matches_current_head", tag_manifest.get("commit") == current_head, {
        "tag_manifest_commit": tag_manifest.get("commit"),
        "current_head": current_head,
    })
    check("tarball_exists", TARBALL.exists(), str(TARBALL))
    check("zip_exists", ZIPFILE.exists(), str(ZIPFILE))
    check("tarball_hash_matches_manifest", tar_hash == manifest.get("archives", {}).get("tarball", {}).get("sha256"), {
        "actual": tar_hash,
        "manifest": manifest.get("archives", {}).get("tarball", {}).get("sha256"),
    })
    check("zip_hash_matches_manifest", zip_hash == manifest.get("archives", {}).get("zip", {}).get("sha256"), {
        "actual": zip_hash,
        "manifest": manifest.get("archives", {}).get("zip", {}).get("sha256"),
    })
    check("production_db_not_touched", manifest.get("production_db_touched") is False, manifest.get("production_db_touched"))
    check("real_config_upgrade_not_run", manifest.get("real_config_upgrade_run") is False, manifest.get("real_config_upgrade_run"))

    # Expected after refresh: release/dist files may be modified before this v12.10.53A commit.
    allowed_dirty_prefixes = (
        "release/v12_10_53/",
        "release/v12_10_53A/",
        "release/V12_10_53A_POST_COMMIT_PACKAGE_REFRESH.md",
        "dist/SOCMINT-PROJECT-v12.10.53-release.tar.gz",
        "dist/SOCMINT-PROJECT-v12.10.53-release.zip",
        "scripts/post_commit_package_refresh_v12_10_53A.py",
        "scripts/test_v12_10_53A.sh",
        "tests/test_v12_10_53A_post_commit_package_refresh.py",
        "Makefile",
        "pyproject.toml",
        "src/socmint/__init__.py",
    )

    unexpected_dirty = []
    for line in git_status.splitlines():
        if not line.strip():
            continue
        path = line[3:] if len(line) > 3 else line
        if not any(path.startswith(prefix) or path == prefix for prefix in allowed_dirty_prefixes):
            unexpected_dirty.append(line)

    check("working_tree_has_no_unexpected_changes", not unexpected_dirty, unexpected_dirty, hard=False)

    tag_ready = len(errors) == 0

    output = {
        "version": VERSION,
        "generated_at": now(),
        "tag_ready": tag_ready,
        "release_status": "PASS GO" if tag_ready else "HOLD",
        "branch": branch,
        "before_head": before_head,
        "before_short": before_short,
        "current_head": current_head,
        "current_short": current_short,
        "manifest_commit": manifest.get("commit"),
        "manifest_full_commit": manifest.get("full_commit"),
        "tag_manifest_commit": tag_manifest.get("commit"),
        "alembic_head": EXPECTED_HEAD if EXPECTED_HEAD in heads_out else heads_out,
        "schema_lock": manifest.get("schema_lock"),
        "production_db_touched": False,
        "real_config_upgrade_run": False,
        "tarball": str(TARBALL),
        "tarball_sha256": tar_hash,
        "zip": str(ZIPFILE),
        "zip_sha256": zip_hash,
        "source_manifest": str(SOURCE_MANIFEST),
        "source_tag_manifest": str(SOURCE_TAG_MANIFEST),
        "checks": checks,
        "errors": errors,
        "warnings": warnings,
        "git_status_short": git_status,
        "unexpected_dirty": unexpected_dirty,
        "recommended_tag": "v12.10.53",
        "create_tag_command": "git tag -a v12.10.53 -m 'SOCMINT-PROJECT v12.10.53 release package'",
        "push_tag_command": "git push origin v12.10.53",
        "next_action": "commit v12.10.53A refreshed package outputs, rerun make report121053A once more if desired, then tag current HEAD",
    }

    TAG_READY_JSON.write_text(json.dumps(output, indent=2, sort_keys=True))
    write_report(output)

    print(json.dumps({
        "version": VERSION,
        "tag_ready": tag_ready,
        "release_status": output["release_status"],
        "current_head": current_short,
        "manifest_commit": manifest.get("commit"),
        "alembic_head": output["alembic_head"],
        "schema_lock": output["schema_lock"],
        "error_count": len(errors),
        "warning_count": len(warnings),
        "tarball_sha256": tar_hash,
        "zip_sha256": zip_hash,
        "production_db_touched": False,
        "real_config_upgrade_run": False,
        "tag_ready_manifest": str(TAG_READY_JSON),
        "report": str(REPORT_MD),
    }, indent=2, sort_keys=True))

    return 0 if tag_ready else 1


def write_report(output: Dict[str, Any]) -> None:
    lines = [
        "# v12.10.53A Post-Commit Package Refresh + Tag-Ready Verification",
        "",
        f"- **tag_ready**: `{output['tag_ready']}`",
        f"- **release_status**: `{output['release_status']}`",
        f"- **branch**: `{output['branch']}`",
        f"- **current_head**: `{output['current_short']}`",
        f"- **manifest_commit**: `{output['manifest_commit']}`",
        f"- **alembic_head**: `{output['alembic_head']}`",
        f"- **schema_lock**: `{output['schema_lock']}`",
        "- **production_db_touched**: `False`",
        "- **real_config_upgrade_run**: `False`",
        f"- **tarball_sha256**: `{output['tarball_sha256']}`",
        f"- **zip_sha256**: `{output['zip_sha256']}`",
        "",
        "## Checks",
        "",
    ]

    for check in output["checks"]:
        mark = "PASS" if check["ok"] else ("WARN" if not check["hard"] else "FAIL")
        lines.append(f"- **{mark}** `{check['name']}` — `{check['detail']}`")

    lines.extend(["", "## Errors", ""])
    if output["errors"]:
        for err in output["errors"]:
            lines.append(f"- {err}")
    else:
        lines.append("- none")

    lines.extend(["", "## Warnings", ""])
    if output["warnings"]:
        for warning in output["warnings"]:
            lines.append(f"- {warning}")
    else:
        lines.append("- none")

    lines.extend([
        "",
        "## Tag commands",
        "",
        "Do not run these until after committing the refreshed v12.10.53A package outputs.",
        "",
        "```bash",
        output["create_tag_command"],
        output["push_tag_command"],
        "```",
        "",
        "## Next action",
        "",
        output["next_action"],
    ])

    REPORT_MD.write_text("\n".join(lines))


if __name__ == "__main__":
    raise SystemExit(main())
