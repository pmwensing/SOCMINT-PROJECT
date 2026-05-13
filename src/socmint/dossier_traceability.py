from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_id(value: str) -> str:
    return "".join(c for c in value if c.isalnum() or c in "-_") or "subject"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    try:
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""


def files_under(roots: list[Path]) -> list[Path]:
    out: list[Path] = []
    for root in roots:
        if root.exists():
            out.extend(p for p in root.rglob("*") if p.is_file())
    return sorted(set(out))


def evidence_to_dossier_traceability(subject_id: str) -> dict[str, Any]:
    sid = subject_id.lower()

    all_files = files_under([Path("storage"), Path("data"), Path("release")])
    dossier_files = [
        p for p in all_files
        if p.suffix.lower() in {".json", ".md", ".txt", ".html", ".pdf"}
        and (sid in p.name.lower() or "dossier" in p.name.lower() or "report" in p.name.lower())
    ][:100]

    evidence_files = [
        p for p in all_files
        if any(x in str(p).lower() for x in ["evidence", "artifact", "vault", "connector", "source"])
    ][:300]

    manifest = [
        {
            "path": str(p),
            "filename": p.name,
            "size": p.stat().st_size if p.exists() else 0,
            "sha256": sha256_file(p),
        }
        for p in evidence_files
    ]

    total_claims = len(dossier_files)
    linked_claims = min(total_claims, len(evidence_files))
    coverage = round((linked_claims / total_claims) * 100, 2) if total_claims else 0.0

    status = "pass" if coverage >= 80 else "warn" if coverage >= 40 or total_claims == 0 else "fail"

    out = {
        "status": status,
        "generated_at": now_iso(),
        "subject_id": subject_id,
        "coverage_percent": coverage,
        "total_claims_detected": total_claims,
        "linked_claims": linked_claims,
        "unresolved_claims": max(total_claims - linked_claims, 0),
        "dossier_files": [str(p) for p in dossier_files],
        "evidence_manifest": manifest,
        "recommended_fixes": [] if status == "pass" else [
            "Attach evidence IDs/source URLs to unsupported claims.",
            "Include source manifest in dossier export.",
            "Regenerate dossier after artifact linking.",
        ],
    }

    dest = Path("storage/traceability")
    dest.mkdir(parents=True, exist_ok=True)
    (dest / f"{safe_id(subject_id)}_traceability.json").write_text(json.dumps(out, indent=2))
    return out
