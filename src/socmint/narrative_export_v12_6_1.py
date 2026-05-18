from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .narrative_intelligence_v12_6 import story_reconstruction_payload

SCHEMA = "socmint.narrative_export.v12_6_1"
DOSSIER_STORY_SCHEMA = "socmint.dossier_auto_story.v12_6_1"


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def narrative_export_root(root: str | None = None) -> Path:
    base = Path(root or "var/socmint")
    return base / "narrative_exports"


def _stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d_%H%M%S")


def story_export_payload(subject_id: int | None = None, root: str | None = None) -> dict[str, Any]:
    story = story_reconstruction_payload(root=root, subject_id=subject_id)
    narrative = story.get("court_lawyer_ready_narrative", {})
    confidence = story.get("narrative_confidence", {})
    return {
        "schema": SCHEMA,
        "generated_at": utc_now(),
        "subject_id": subject_id,
        "narrative_confidence": confidence,
        "timeline_event_count": story.get("timeline", {}).get("event_count", 0),
        "claim_count": len(story.get("claims", [])),
        "contradiction_count": story.get("contradictions", {}).get("contradiction_count", 0),
        "markdown": narrative.get("markdown", ""),
        "plain_text": narrative.get("plain_text", ""),
        "story_payload": story,
    }


def write_story_exports(subject_id: int | None = None, root: str | None = None) -> dict[str, Any]:
    payload = story_export_payload(subject_id=subject_id, root=root)
    out = narrative_export_root(root)
    out.mkdir(parents=True, exist_ok=True)
    suffix = f"subject_{subject_id}" if subject_id is not None else "case"
    base = out / f"narrative_story_{suffix}_{_stamp()}"
    json_path = base.with_suffix(".json")
    md_path = base.with_suffix(".md")
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    md_path.write_text(payload.get("markdown") or "# Narrative Intelligence Brief\n\nNo narrative generated.\n")
    return {
        "schema": SCHEMA,
        "generated_at": utc_now(),
        "subject_id": subject_id,
        "json_path": str(json_path),
        "markdown_path": str(md_path),
        "summary": {
            "confidence": payload.get("narrative_confidence"),
            "timeline_event_count": payload.get("timeline_event_count"),
            "claim_count": payload.get("claim_count"),
            "contradiction_count": payload.get("contradiction_count"),
        },
    }


def dossier_story_layer(subject_id: int, root: str | None = None) -> dict[str, Any]:
    export = story_export_payload(subject_id=subject_id, root=root)
    story = export.get("story_payload", {})
    return {
        "schema": DOSSIER_STORY_SCHEMA,
        "generated_at": utc_now(),
        "subject_id": subject_id,
        "status": "ready_for_review" if export.get("timeline_event_count", 0) else "insufficient_events",
        "narrative_confidence": export.get("narrative_confidence"),
        "summary": (export.get("plain_text") or "")[:2000],
        "timeline_event_count": export.get("timeline_event_count"),
        "claim_count": export.get("claim_count"),
        "contradiction_count": export.get("contradiction_count"),
        "top_events": story.get("event_sequence", [])[:10],
        "top_claims": story.get("claim_validation", {}).get("validated_claims", [])[:10],
        "requires_human_review": True,
        "legal_use_note": "Auto-story output is an analytical aid and must be reviewed before filing, service, or legal use.",
    }


def narrative_dashboard_polish_payload(subject_id: int | None = None, root: str | None = None, sort: str = "timestamp", event_type: str | None = None) -> dict[str, Any]:
    story = story_reconstruction_payload(root=root, subject_id=subject_id)
    events = list(story.get("event_sequence", []))
    if event_type:
        events = [event for event in events if event.get("event_type") == event_type]
    if sort == "confidence":
        events.sort(key=lambda item: float(item.get("confidence") or 0), reverse=True)
    else:
        events.sort(key=lambda item: str(item.get("timestamp") or ""))
    claims_by_evidence: dict[str, list[dict[str, Any]]] = {}
    for claim in story.get("claim_validation", {}).get("validated_claims", []):
        evidence_id = claim.get("evidence_id") or "case"
        claims_by_evidence.setdefault(evidence_id, []).append(claim)
    contradiction_actions = []
    for index, issue in enumerate(story.get("contradictions", {}).get("contradictions", []), start=1):
        contradiction_actions.append({
            "id": f"ctr-{index:04d}",
            "state": "needs_review",
            "action": "review_and_mark_resolved_or_escalate",
            "issue": issue,
            "notes": "Analyst must inspect source claims before using narrative output.",
        })
    return {
        "schema": "socmint.narrative_dashboard_polish.v12_6_1",
        "generated_at": utc_now(),
        "subject_id": subject_id,
        "sort": sort,
        "event_type_filter": event_type,
        "events": events,
        "claims_by_evidence": claims_by_evidence,
        "contradiction_review_actions": contradiction_actions,
        "narrative_confidence_card": story.get("narrative_confidence", {}),
        "story_export_preview": story.get("court_lawyer_ready_narrative", {}),
        "dossier_story_layer": dossier_story_layer(subject_id, root=root) if subject_id is not None else None,
        "base_story": story,
    }
