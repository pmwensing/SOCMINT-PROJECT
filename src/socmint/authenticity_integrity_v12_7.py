from __future__ import annotations

import json
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .forensic_intake_v12_5 import manifests_root

SCHEMA = "socmint.authenticity_integrity.v12_7"
DASHBOARD_SCHEMA = "socmint.evidence_integrity_dashboard.v12_7"

SCREENSHOT_HINTS = {
    "screenshot",
    "screen shot",
    "capture",
    "img_",
    "photo_",
    "whatsapp",
    "telegram",
    "signal",
    "messenger",
}
PDF_PRODUCER_RECONSTRUCTION_HINTS = {
    "scanner",
    "scan",
    "print",
    "microsoft print",
    "pdfcreator",
    "wkhtmltopdf",
    "ghostscript",
    "pypdf",
    "itext",
    "tx_pdf",
    "pdf library",
}
MEDIA_EDITOR_HINTS = {
    "photoshop",
    "gimp",
    "lightroom",
    "snapseed",
    "canva",
    "paint",
    "preview",
    "pixelmator",
    "capcut",
    "premiere",
    "final cut",
    "after effects",
}


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _manifest_items(root: str | None = None) -> list[dict[str, Any]]:
    directory = manifests_root(root)
    items: list[dict[str, Any]] = []
    if not directory.exists():
        return items
    for path in sorted(directory.glob("forensic_preservation_manifest_*.json")):
        payload = _load_json(path) or {}
        for item in payload.get("items", []):
            row = dict(item)
            row["manifest_path"] = str(path)
            items.append(row)
    return items


def _metadata_text(item: dict[str, Any]) -> str:
    return json.dumps(item.get("metadata") or {}, sort_keys=True, default=str).lower()


def _filename(item: dict[str, Any]) -> str:
    meta = item.get("metadata") or {}
    return str(
        meta.get("filename") or Path(item.get("preserved_path") or "").name or ""
    ).lower()


def _metadata_tool_payload(item: dict[str, Any], tool: str) -> dict[str, Any] | None:
    meta = item.get("metadata") or {}
    payload = meta.get(tool)
    if isinstance(payload, dict):
        return payload
    return None


def detect_metadata_mismatches(item: dict[str, Any]) -> list[dict[str, Any]]:
    flags: list[dict[str, Any]] = []
    kind = item.get("kind") or "unknown"
    metadata = item.get("metadata") or {}
    mime_guess = metadata.get("mime_guess")
    ext = str(metadata.get("extension") or "").lower()
    expected_by_ext = {
        ".jpg": "image",
        ".jpeg": "image",
        ".png": "image",
        ".gif": "image",
        ".webp": "image",
        ".mp4": "video",
        ".mov": "video",
        ".mkv": "video",
        ".avi": "video",
        ".mp3": "audio",
        ".wav": "audio",
        ".m4a": "audio",
        ".pdf": "document",
        ".docx": "document",
        ".txt": "document",
        ".csv": "document",
        ".eml": "email_export",
        ".mbox": "email_export",
    }
    expected = expected_by_ext.get(ext)
    if expected and expected != kind:
        flags.append(
            {
                "type": "extension_kind_mismatch",
                "severity": "high",
                "expected": expected,
                "actual": kind,
                "extension": ext,
            }
        )
    if mime_guess and kind == "image" and not str(mime_guess).startswith("image/"):
        flags.append(
            {
                "type": "mime_kind_mismatch",
                "severity": "high",
                "mime": mime_guess,
                "kind": kind,
            }
        )
    if mime_guess and kind == "video" and not str(mime_guess).startswith("video/"):
        flags.append(
            {
                "type": "mime_kind_mismatch",
                "severity": "high",
                "mime": mime_guess,
                "kind": kind,
            }
        )
    if item.get("original_sha256") != item.get("preserved_sha256"):
        flags.append(
            {
                "type": "hash_mismatch",
                "severity": "critical",
                "original_sha256": item.get("original_sha256"),
                "preserved_sha256": item.get("preserved_sha256"),
            }
        )
    if not ((item.get("court_safe") or {}).get("hash_verified")):
        flags.append({"type": "hash_not_verified", "severity": "critical"})
    return flags


def detect_tamper_flags(item: dict[str, Any]) -> list[dict[str, Any]]:
    flags: list[dict[str, Any]] = []
    kind = item.get("kind") or "unknown"
    text = _metadata_text(item)
    filename = _filename(item)
    if kind == "image" and any(hint in filename for hint in SCREENSHOT_HINTS):
        flags.append(
            {
                "type": "screenshot_or_messaging_capture",
                "severity": "review",
                "reason": "filename suggests screenshot or social/messaging capture",
            }
        )
    if kind == "image" and "exiftool" not in (item.get("metadata") or {}):
        flags.append(
            {
                "type": "image_missing_exiftool_metadata",
                "severity": "review",
                "reason": "ExifTool metadata not available; install exiftool for deeper checks",
            }
        )
    if (
        kind == "document"
        and filename.endswith(".pdf")
        and any(hint in text for hint in PDF_PRODUCER_RECONSTRUCTION_HINTS)
    ):
        flags.append(
            {
                "type": "pdf_reconstruction_or_generated_pdf_hint",
                "severity": "review",
                "reason": "metadata producer/tool hints suggest generated, scanned, or reconstructed PDF",
            }
        )
    if kind in {"image", "video"} and any(hint in text for hint in MEDIA_EDITOR_HINTS):
        flags.append(
            {
                "type": "media_editor_metadata_hint",
                "severity": "review",
                "reason": "metadata contains common editor/tool names",
            }
        )
    if kind in {"video", "audio"} and "ffprobe" not in (item.get("metadata") or {}):
        flags.append(
            {
                "type": "media_probe_missing",
                "severity": "review",
                "reason": "ffprobe metadata not available; install ffmpeg/ffprobe for deeper checks",
            }
        )
    preserved_path = str(item.get("preserved_path") or "")
    if preserved_path and not Path(preserved_path).exists():
        flags.append(
            {
                "type": "preserved_file_missing",
                "severity": "critical",
                "reason": "vault original path is missing",
            }
        )
    return flags


def authenticity_score(item: dict[str, Any]) -> dict[str, Any]:
    mismatch_flags = detect_metadata_mismatches(item)
    tamper_flags = detect_tamper_flags(item)
    flags = mismatch_flags + tamper_flags
    score = 1.0
    for flag in flags:
        severity = flag.get("severity")
        if severity == "critical":
            score -= 0.35
        elif severity == "high":
            score -= 0.2
        elif severity == "review":
            score -= 0.08
        else:
            score -= 0.04
    if (item.get("court_safe") or {}).get("hash_verified"):
        score += 0.08
    if item.get("custody"):
        score += 0.05
    score = max(0.0, min(1.0, score))
    if score >= 0.85:
        rating = "strong"
    elif score >= 0.65:
        rating = "moderate"
    elif score >= 0.4:
        rating = "weak"
    else:
        rating = "fail"
    return {
        "score": round(score, 3),
        "rating": rating,
        "flags": flags,
        "tamper_flag_count": len(tamper_flags),
        "metadata_mismatch_count": len(mismatch_flags),
    }


def provenance_confidence(item: dict[str, Any]) -> dict[str, Any]:
    custody_events = item.get("custody") or []
    has_manifest = bool(item.get("manifest_path"))
    hash_verified = bool((item.get("court_safe") or {}).get("hash_verified"))
    source_path = str(item.get("original_path") or "")
    preserved_path = str(item.get("preserved_path") or "")
    score = 0.25
    if hash_verified:
        score += 0.35
    if custody_events:
        score += min(0.2, len(custody_events) * 0.06)
    if has_manifest:
        score += 0.1
    if source_path:
        score += 0.05
    if preserved_path and Path(preserved_path).exists():
        score += 0.05
    score = max(0.0, min(1.0, score))
    return {
        "score": round(score, 3),
        "rating": "strong"
        if score >= 0.8
        else "moderate"
        if score >= 0.6
        else "weak"
        if score >= 0.35
        else "fail",
        "factors": {
            "hash_verified": hash_verified,
            "custody_event_count": len(custody_events),
            "manifest_linked": has_manifest,
            "source_path_present": bool(source_path),
            "preserved_path_exists": bool(
                preserved_path and Path(preserved_path).exists()
            ),
        },
    }


def classify_evidence_surface(item: dict[str, Any]) -> str:
    kind = item.get("kind") or "unknown"
    filename = _filename(item)
    if kind == "image" and any(hint in filename for hint in SCREENSHOT_HINTS):
        return "screenshot"
    if kind == "document" and filename.endswith(".pdf"):
        return "pdf"
    if kind in {"image", "video", "audio"}:
        return "media"
    return kind


def analyze_evidence_item(item: dict[str, Any]) -> dict[str, Any]:
    authenticity = authenticity_score(item)
    provenance = provenance_confidence(item)
    composite = round((authenticity["score"] * 0.55) + (provenance["score"] * 0.45), 3)
    if authenticity["rating"] == "fail" or provenance["rating"] == "fail":
        decision = "fail"
    elif composite >= 0.8:
        decision = "court-ready-review"
    elif composite >= 0.6:
        decision = "analyst-review"
    else:
        decision = "hold"
    return {
        "schema": SCHEMA,
        "evidence_id": item.get("evidence_id"),
        "kind": item.get("kind"),
        "surface": classify_evidence_surface(item),
        "filename": (item.get("metadata") or {}).get("filename"),
        "preserved_path": item.get("preserved_path"),
        "authenticity": authenticity,
        "provenance_confidence": provenance,
        "composite_score": composite,
        "decision": decision,
        "requires_human_review": decision != "court-ready-review"
        or bool(authenticity.get("flags")),
        "legal_use_note": "Authenticity scoring is an analytical aid. Human review and source verification remain required before legal use.",
    }


def integrity_dashboard_payload(root: str | None = None) -> dict[str, Any]:
    items = _manifest_items(root)
    analyses = [analyze_evidence_item(item) for item in items]
    ratings = Counter(row["authenticity"]["rating"] for row in analyses)
    decisions = Counter(row["decision"] for row in analyses)
    surfaces = Counter(row["surface"] for row in analyses)
    flagged = [row for row in analyses if row["authenticity"].get("flags")]
    return {
        "schema": DASHBOARD_SCHEMA,
        "generated_at": utc_now(),
        "item_count": len(analyses),
        "flagged_count": len(flagged),
        "summary": {
            "ratings": dict(ratings),
            "decisions": dict(decisions),
            "surfaces": dict(surfaces),
            "avg_composite_score": round(
                sum(row["composite_score"] for row in analyses) / max(1, len(analyses)),
                3,
            ),
        },
        "analyses": analyses,
        "flagged_items": flagged,
        "rules": [
            "Hash mismatch or missing preserved original is critical.",
            "Screenshot/social capture evidence requires analyst review.",
            "Generated/scanned/reconstructed PDF metadata is a review flag, not automatic rejection.",
            "Media editor metadata is a review flag requiring provenance explanation.",
            "Court-ready-review still requires human verification before legal use.",
        ],
    }


if __name__ == "__main__":
    print(json.dumps(integrity_dashboard_payload(), indent=2, sort_keys=True))
