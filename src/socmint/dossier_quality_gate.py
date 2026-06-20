from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_id(value: str) -> str:
    return "".join(c for c in value if c.isalnum() or c in "-_") or "subject"


def find_subject_files(subject_id: str) -> list[Path]:
    roots = [
        Path("storage/exports"),
        Path("storage/dossiers"),
        Path("storage/reports"),
        Path("data"),
        Path("release"),
    ]
    sid = subject_id.lower()
    out: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if p.is_file() and p.suffix.lower() in {".json", ".md", ".txt", ".html"}:
                if (
                    sid in p.name.lower()
                    or "dossier" in p.name.lower()
                    or "report" in p.name.lower()
                ):
                    out.append(p)
    return sorted(set(out))


def read_text(path: Path, limit: int = 1_000_000) -> str:
    try:
        return path.read_text(errors="replace")[:limit]
    except Exception:
        return ""


def issue(
    blocking: bool, code: str, message: str, recommendation: str
) -> dict[str, Any]:
    return {
        "blocking": blocking,
        "code": code,
        "message": message,
        "recommendation": recommendation,
    }


def dossier_quality_gate(subject_id: str) -> dict[str, Any]:
    files = find_subject_files(subject_id)
    text = "\n\n".join(read_text(p) for p in files[:25]).lower()

    warnings: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []

    if not files:
        warnings.append(
            issue(
                False,
                "no_matching_dossier_files",
                "No matching dossier/export files found.",
                "Generate a dossier export and rerun the quality gate.",
            )
        )
    if files and not any(k in text for k in ["source", "citation", "evidence"]):
        blockers.append(
            issue(
                True,
                "missing_sources",
                "No source/citation/evidence references detected.",
                "Attach source manifest or citation map.",
            )
        )
    if files and not any(k in text for k in ["executive summary", "summary"]):
        warnings.append(
            issue(
                False,
                "missing_summary",
                "No summary section detected.",
                "Add executive summary.",
            )
        )
    if files and not any(k in text for k in ["timeline", "event"]):
        warnings.append(
            issue(
                False,
                "missing_timeline",
                "No timeline/event anchors detected.",
                "Add timeline anchors.",
            )
        )
    if files and not any(k in text for k in ["confidence", "score"]):
        warnings.append(
            issue(
                False,
                "missing_confidence",
                "No confidence scoring detected.",
                "Add confidence ratings.",
            )
        )

    score = max(0, 100 - len(blockers) * 25 - len(warnings) * 8)
    status = "fail" if blockers else "warn" if warnings else "pass"

    out = {
        "status": status,
        "score": score,
        "generated_at": now_iso(),
        "subject_id": subject_id,
        "files_evaluated": [str(p) for p in files[:25]],
        "blocking_issues": blockers,
        "warnings": warnings,
        "recommended_fixes": [x["recommendation"] for x in blockers + warnings],
    }

    dest = Path("storage/dossier_quality")
    dest.mkdir(parents=True, exist_ok=True)
    (dest / f"{safe_id(subject_id)}_quality_gate.json").write_text(
        json.dumps(out, indent=2)
    )
    return out
