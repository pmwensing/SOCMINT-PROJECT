from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from typing import Any

QUALITY_SCHEMA = "socmint.v7_5.dossier_quality_gate"
REPORTABLE_SECTIONS = [
    "accounts",
    "evidence_backed_attributes",
    "timeline",
    "relationships",
    "contradictions",
]


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _has_evidence_refs(item: dict[str, Any]) -> bool:
    refs = item.get("evidence_refs") or item.get("evidence_ids") or []
    if refs:
        return True
    return bool(item.get("evidence_id") or item.get("artifact_id") or item.get("source_ref"))


def _has_source(item: dict[str, Any]) -> bool:
    if item.get("source") or item.get("source_url") or item.get("platform"):
        return True
    refs = item.get("source_refs") or []
    return bool(refs)


def _has_confidence(item: dict[str, Any]) -> bool:
    if "confidence" in item and item.get("confidence") not in (None, ""):
        return True
    if item.get("status") == "conflict" and _has_evidence_refs(item):
        return True
    return False


def _claim_label(section: str, item: dict[str, Any]) -> str:
    return str(
        item.get("name")
        or item.get("claim")
        or item.get("event")
        or item.get("relationship")
        or item.get("handle")
        or item.get("url")
        or item.get("target")
        or item.get("platform")
        or item.get("id")
        or section
    )


def _iter_reportable_items(payload: dict[str, Any]):
    for section in REPORTABLE_SECTIONS:
        items = payload.get(section) or []
        if not isinstance(items, list):
            continue
        for index, item in enumerate(items):
            if isinstance(item, dict):
                yield section, index, item


def _preflight_note(payload: dict[str, Any]) -> dict[str, Any] | None:
    preflight = payload.get("export_preflight") or {}
    if isinstance(preflight, dict) and preflight.get("ready") is False:
        return {
            "status": "note",
            "section": "export_preflight",
            "index": None,
            "claim": "export_preflight",
            "missing": [],
            "detail": "Existing export preflight reports the dossier is not ready. This is tracked separately from the v7.5 claim-context gate.",
        }
    return None


def evaluate_dossier_quality(payload: dict[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    section_counts: Counter[str] = Counter()
    missing_counts: Counter[str] = Counter()

    for section, index, item in _iter_reportable_items(payload):
        section_counts[section] += 1
        missing = []
        if not _has_evidence_refs(item):
            missing.append("evidence_refs")
        if not _has_source(item):
            missing.append("source")
        if not _has_confidence(item):
            missing.append("confidence")
        for field in missing:
            missing_counts[field] += 1
        if missing:
            findings.append(
                {
                    "status": "fail",
                    "section": section,
                    "index": index,
                    "claim": _claim_label(section, item),
                    "missing": missing,
                    "detail": "Reportable dossier item is missing required source/evidence/confidence context.",
                }
            )

    status = "fail" if findings else "pass"
    notes = []
    note = _preflight_note(payload)
    if note:
        notes.append(note)

    return {
        "schema": QUALITY_SCHEMA,
        "generated_at": utc_now(),
        "status": status,
        "approved_line": "v7.5",
        "rule": "No report claim without source/evidence/confidence context.",
        "reportable_section_counts": dict(sorted(section_counts.items())),
        "missing_context_counts": dict(sorted(missing_counts.items())),
        "finding_count": len(findings),
        "findings": findings,
        "note_count": len(notes),
        "notes": notes,
    }


def attach_dossier_quality(payload: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(payload)
    enriched["quality_gate"] = evaluate_dossier_quality(payload)
    enriched["export_ready"] = enriched["quality_gate"]["status"] == "pass"
    return enriched
