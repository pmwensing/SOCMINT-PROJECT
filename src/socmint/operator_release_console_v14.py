from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any


OPERATOR_RELEASE_CONSOLE_SCHEMA = "socmint.operator_release_console.v14_0"
DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]

REQUIRED_RELEASE_DOCS = [
    {
        "key": "v13_documentation_closure",
        "label": "v13 documentation closure",
        "path": "release/V13_RELEASE_DOCUMENTATION_CLOSURE.md",
    },
    {
        "key": "v13_sequence_audit",
        "label": "v13 sequence audit",
        "path": "release/V13_RELEASE_SEQUENCE_AUDIT.md",
    },
    {
        "key": "v13_35_final_closure",
        "label": "v13.35 final closure",
        "path": "release/V13_35_FINAL_CORRELATION_SCOPE_CLOSURE.md",
    },
    {
        "key": "v13_export_blocker_index",
        "label": "v13.36-v13.44 export-blocker index",
        "path": "release/V13_36_TO_44_EXPORT_BLOCKER_INDEX.md",
    },
    {
        "key": "v13_export_workflow_index",
        "label": "v13.45-v13.48 export-blocker workflow index",
        "path": "release/V13_45_TO_48_EXPORT_BLOCKER_WORKFLOW_INDEX.md",
    },
    {
        "key": "v13_reserved_gap",
        "label": "v13.25 reserved gap",
        "path": "release/V13_25_RESERVED_GAP.md",
    },
    {
        "key": "v10_open_pr_triage",
        "label": "v10.32-v10.37 stale PR triage",
        "path": "release/V10_32_TO_37_OPEN_PR_TRIAGE.md",
    },
    {
        "key": "open_pr_queue_closure",
        "label": "open PR queue closure",
        "path": "release/OPEN_PR_QUEUE_CLOSURE.md",
    },
]


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _git_value(root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return value or None


def _status_item(key: str, label: str, ok: bool, source: str, detail: str) -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "status": "pass" if ok else "needs_review",
        "ok": ok,
        "source": source,
        "detail": detail,
    }


def _release_doc_items(root: Path) -> list[dict[str, Any]]:
    items = []
    for doc in REQUIRED_RELEASE_DOCS:
        path = root / doc["path"]
        exists = path.exists()
        items.append(
            _status_item(
                doc["key"],
                doc["label"],
                exists,
                doc["path"],
                "present" if exists else "missing",
            )
        )
    return items


def _changelog_item(root: Path) -> dict[str, Any]:
    changelog = _read_text(root / "CHANGELOG.md")
    has_entry = "v14.0 Operator Release Console" in changelog
    return _status_item(
        "changelog_entry",
        "v14.0 changelog entry",
        has_entry,
        "CHANGELOG.md",
        "present" if has_entry else "missing",
    )


def _git_summary(root: Path) -> dict[str, Any]:
    dirty = _git_value(root, "status", "--porcelain")
    return {
        "available": _git_value(root, "rev-parse", "--is-inside-work-tree") == "true",
        "branch": _git_value(root, "branch", "--show-current"),
        "commit": _git_value(root, "rev-parse", "--short", "HEAD"),
        "latest_tag": _git_value(root, "describe", "--tags", "--abbrev=0"),
        "dirty": bool(dirty),
        "dirty_detail": "uncommitted changes present" if dirty else "clean",
    }


def _queue_summary(root: Path) -> dict[str, Any]:
    closure = _read_text(root / "release/OPEN_PR_QUEUE_CLOSURE.md")
    triage = _read_text(root / "release/V10_32_TO_37_OPEN_PR_TRIAGE.md")
    closed_refs = [f"#{number}" for number in range(139, 145) if f"#{number}" in closure]
    closure_present = bool(closure)
    return {
        "status": "clean_documented" if closure_present and len(closed_refs) == 6 else "needs_review",
        "source": "release/OPEN_PR_QUEUE_CLOSURE.md" if closure_present else "release/V10_32_TO_37_OPEN_PR_TRIAGE.md",
        "closed_superseded_prs": closed_refs,
        "triage_available": bool(triage),
        "live_open_pr_count": os.environ.get("SOCMINT_RELEASE_CONSOLE_OPEN_PR_COUNT"),
        "note": (
            "clean queue documented from local release artifact"
            if closure_present and len(closed_refs) == 6
            else "local closure artifact missing or incomplete"
        ),
    }


def operator_release_console_payload(root: str | Path | None = None) -> dict[str, Any]:
    repo_root = Path(root) if root is not None else DEFAULT_REPO_ROOT
    repo_root = repo_root.resolve()
    release_docs = _release_doc_items(repo_root)
    changelog_item = _changelog_item(repo_root)
    queue = _queue_summary(repo_root)
    git = _git_summary(repo_root)
    checks = release_docs + [changelog_item]
    checks.append(
        _status_item(
            "open_pr_queue_clean",
            "open PR queue clean",
            queue["status"] == "clean_documented",
            queue["source"],
            queue["note"],
        )
    )
    checks.append(
        _status_item(
            "git_metadata",
            "local git metadata",
            bool(git["available"] and git["commit"]),
            "git",
            git["dirty_detail"],
        )
    )

    passed = sum(1 for item in checks if item["ok"])
    failed = len(checks) - passed
    decision = "GO_FOR_V14" if failed == 0 else "HOLD_FOR_RELEASE_REPAIR"
    next_action = (
        "Continue v14 implementation line from the operator release console."
        if decision == "GO_FOR_V14"
        else "Repair missing release evidence before extending the release line."
    )

    return {
        "schema": OPERATOR_RELEASE_CONSOLE_SCHEMA,
        "release_line": "v14.0",
        "title": "Operator Release Console",
        "decision": decision,
        "status": "pass" if failed == 0 else "needs_review",
        "summary": {
            "passed": passed,
            "needs_review": failed,
            "total": len(checks),
            "next_action": next_action,
        },
        "git": git,
        "pr_queue": queue,
        "checks": checks,
        "sources": {
            "repo_root": str(repo_root),
            "release_docs": [doc["path"] for doc in REQUIRED_RELEASE_DOCS],
            "changelog": "CHANGELOG.md",
        },
    }
