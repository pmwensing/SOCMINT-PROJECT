from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .forensic_intake_v12_5 import manifests_root

try:
    from .spine_intelligence_v11_9 import spine_intelligence_payload
except Exception:  # pragma: no cover
    spine_intelligence_payload = None

SCHEMA = "socmint.narrative_intelligence.v12_6"
TIMELINE_SCHEMA = "socmint.narrative_timeline.v12_6"
CONTRADICTION_SCHEMA = "socmint.contradiction_engine.v12_6"
GRAPH_SCHEMA = "socmint.communication_graph.v12_6"

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}(?!\d)")


@dataclass
class NarrativeEvent:
    event_id: str
    timestamp: str
    event_type: str
    title: str
    description: str
    source: str
    evidence_id: str | None = None
    confidence: float = 0.5
    tags: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Claim:
    claim_id: str
    subject: str
    predicate: str
    value: str
    source: str
    evidence_id: str | None = None
    confidence: float = 0.5
    polarity: str = "asserted"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _safe_dt(value: str | None) -> str:
    if not value:
        return utc_now()
    return str(value)


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
            item = dict(item)
            item["manifest_path"] = str(path)
            items.append(item)
    return items


def evidence_to_timeline(root: str | None = None, subject_id: int | None = None) -> dict[str, Any]:
    events: list[NarrativeEvent] = []
    for index, item in enumerate(_manifest_items(root), start=1):
        evidence_id = item.get("evidence_id")
        kind = item.get("kind") or "evidence"
        meta = item.get("metadata") or {}
        title = f"{kind.replace('_', ' ').title()} preserved: {meta.get('filename') or evidence_id}"
        hash_verified = bool((item.get("court_safe") or {}).get("hash_verified"))
        confidence = 0.85 if hash_verified else 0.55
        events.append(NarrativeEvent(
            event_id=f"ev-{index:04d}",
            timestamp=_safe_dt(item.get("ingested_at") or meta.get("mtime")),
            event_type="evidence_preserved",
            title=title,
            description=f"Evidence {evidence_id} was preserved as {kind}; hash verification: {hash_verified}.",
            source="forensic_intake_manifest",
            evidence_id=evidence_id,
            confidence=confidence,
            tags=[kind, "court_safe" if hash_verified else "review"],
            raw=item,
        ))
    if subject_id is not None and spine_intelligence_payload is not None:
        try:
            spine = spine_intelligence_payload(subject_id)
            for run in spine.get("runs", []):
                events.append(NarrativeEvent(
                    event_id=f"connector-{run.get('id', len(events) + 1)}",
                    timestamp=_safe_dt(run.get("created_at") or run.get("updated_at")),
                    event_type="connector_run",
                    title=f"Connector run: {run.get('connector', 'unknown')}",
                    description=run.get("explanation") or f"Connector status: {run.get('status')}",
                    source="spine_intelligence",
                    confidence=0.75 if run.get("badge") == "real" else 0.4,
                    tags=[run.get("status") or "unknown", run.get("badge") or "review"],
                    raw=run,
                ))
        except Exception:
            pass
    events.sort(key=lambda item: item.timestamp)
    return {"schema": TIMELINE_SCHEMA, "generated_at": utc_now(), "event_count": len(events), "events": [event.as_dict() for event in events]}


def extract_claims(events: list[dict[str, Any]]) -> list[Claim]:
    claims: list[Claim] = []
    for index, event in enumerate(events, start=1):
        raw = event.get("raw") or {}
        evidence_id = event.get("evidence_id")
        kind = raw.get("kind") or event.get("event_type") or "unknown"
        filename = ((raw.get("metadata") or {}).get("filename") or event.get("title") or "unknown")
        hash_verified = bool((raw.get("court_safe") or {}).get("hash_verified"))
        claims.append(Claim(
            claim_id=f"cl-{index:04d}",
            subject=evidence_id or "case",
            predicate="evidence_kind",
            value=str(kind),
            source=event.get("source") or "unknown",
            evidence_id=evidence_id,
            confidence=0.85 if hash_verified else float(event.get("confidence") or 0.5),
        ))
        claims.append(Claim(
            claim_id=f"cl-{index:04d}-file",
            subject=evidence_id or "case",
            predicate="filename",
            value=str(filename),
            source=event.get("source") or "unknown",
            evidence_id=evidence_id,
            confidence=float(event.get("confidence") or 0.5),
        ))
    return claims


def contradiction_engine(claims: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for claim in claims:
        grouped[(str(claim.get("subject")), str(claim.get("predicate")))].append(claim)
    contradictions = []
    for (subject, predicate), rows in grouped.items():
        values = {str(row.get("value")) for row in rows if row.get("value") is not None}
        polarities = {str(row.get("polarity", "asserted")) for row in rows}
        if len(values) > 1 and predicate not in {"filename"}:
            contradictions.append({
                "type": "conflicting_values",
                "subject": subject,
                "predicate": predicate,
                "values": sorted(values),
                "claims": rows,
                "severity": "review",
            })
        if "denied" in polarities and "asserted" in polarities:
            contradictions.append({
                "type": "asserted_and_denied",
                "subject": subject,
                "predicate": predicate,
                "claims": rows,
                "severity": "high",
            })
    return {"schema": CONTRADICTION_SCHEMA, "generated_at": utc_now(), "contradiction_count": len(contradictions), "contradictions": contradictions}


def communication_graph(events: list[dict[str, Any]]) -> dict[str, Any]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    for event in events:
        text = json.dumps(event, sort_keys=True)
        evidence_id = event.get("evidence_id") or event.get("event_id")
        if evidence_id:
            nodes.setdefault(evidence_id, {"id": evidence_id, "type": "evidence", "label": evidence_id})
        for email in sorted(set(EMAIL_RE.findall(text))):
            nodes.setdefault(email, {"id": email, "type": "email", "label": email})
            if evidence_id:
                edges.append({"source": evidence_id, "target": email, "type": "mentions_email", "confidence": 0.7})
        for phone in sorted(set(PHONE_RE.findall(text))):
            nodes.setdefault(phone, {"id": phone, "type": "phone", "label": phone})
            if evidence_id:
                edges.append({"source": evidence_id, "target": phone, "type": "mentions_phone", "confidence": 0.65})
    return {"schema": GRAPH_SCHEMA, "generated_at": utc_now(), "node_count": len(nodes), "edge_count": len(edges), "nodes": list(nodes.values()), "edges": edges}


def validate_claims(claims: list[dict[str, Any]], events: list[dict[str, Any]]) -> dict[str, Any]:
    event_by_evidence = {event.get("evidence_id"): event for event in events if event.get("evidence_id")}
    validated = []
    for claim in claims:
        evidence_id = claim.get("evidence_id")
        event = event_by_evidence.get(evidence_id)
        hash_verified = bool((((event or {}).get("raw") or {}).get("court_safe") or {}).get("hash_verified"))
        confidence = float(claim.get("confidence") or 0.5)
        if hash_verified:
            confidence = min(0.95, confidence + 0.1)
        maturity = "court-grade" if hash_verified and confidence >= 0.8 else "dossier-grade" if confidence >= 0.7 else "review"
        validated.append({**claim, "validated": hash_verified or confidence >= 0.7, "hash_verified": hash_verified, "maturity": maturity, "confidence": round(confidence, 3)})
    counts = Counter(item["maturity"] for item in validated)
    return {"schema": SCHEMA, "validated_claims": validated, "maturity_counts": dict(counts)}


def narrative_confidence(events: list[dict[str, Any]], claims: list[dict[str, Any]], contradictions: dict[str, Any]) -> dict[str, Any]:
    if not events:
        return {"score": 0.0, "rating": "insufficient", "factors": ["No narrative events found."]}
    avg_event = sum(float(event.get("confidence") or 0.0) for event in events) / len(events)
    court_grade = sum(1 for claim in claims if claim.get("maturity") == "court-grade")
    contradiction_penalty = min(0.35, contradictions.get("contradiction_count", 0) * 0.08)
    score = max(0.0, min(1.0, (avg_event * 0.55) + (min(1.0, court_grade / max(1, len(events))) * 0.35) + 0.1 - contradiction_penalty))
    rating = "strong" if score >= 0.8 else "moderate" if score >= 0.55 else "weak" if score > 0 else "insufficient"
    return {"score": round(score, 3), "rating": rating, "factors": [f"avg_event_confidence={avg_event:.2f}", f"court_grade_claims={court_grade}", f"contradictions={contradictions.get('contradiction_count', 0)}"]}


def generate_court_narrative(events: list[dict[str, Any]], validated: dict[str, Any], contradictions: dict[str, Any], confidence: dict[str, Any]) -> dict[str, str]:
    lines = [
        "# Narrative Intelligence Brief",
        "",
        f"Confidence rating: {confidence.get('rating')} ({confidence.get('score')})",
        "",
        "## Chronology",
    ]
    for event in events[:50]:
        lines.append(f"- {event.get('timestamp')} — {event.get('title')} ({event.get('source')}; confidence {event.get('confidence')})")
    lines.extend(["", "## Validated Claims"])
    for claim in validated.get("validated_claims", [])[:50]:
        lines.append(f"- {claim.get('maturity')}: {claim.get('subject')} {claim.get('predicate')} = {claim.get('value')} [confidence {claim.get('confidence')}]")
    lines.extend(["", "## Contradictions / Review Issues"])
    if contradictions.get("contradictions"):
        for issue in contradictions.get("contradictions", [])[:25]:
            lines.append(f"- {issue.get('severity')}: {issue.get('type')} on {issue.get('subject')} / {issue.get('predicate')}")
    else:
        lines.append("- No deterministic contradictions detected in the current claim set.")
    lines.extend(["", "## Court/Lawyer Use Note", "This narrative is a structured analytical aid. It should be reviewed by an analyst before filing, service, or legal use."])
    markdown = "\n".join(lines) + "\n"
    plain = re.sub(r"[#*`]", "", markdown)
    return {"markdown": markdown, "plain_text": plain}


def story_reconstruction_payload(root: str | None = None, subject_id: int | None = None) -> dict[str, Any]:
    timeline = evidence_to_timeline(root=root, subject_id=subject_id)
    events = timeline.get("events", [])
    claim_objs = extract_claims(events)
    claims = [claim.as_dict() for claim in claim_objs]
    contradictions = contradiction_engine(claims)
    graph = communication_graph(events)
    validated = validate_claims(claims, events)
    confidence = narrative_confidence(events, validated.get("validated_claims", []), contradictions)
    narrative = generate_court_narrative(events, validated, contradictions, confidence)
    return {
        "schema": SCHEMA,
        "generated_at": utc_now(),
        "subject_id": subject_id,
        "timeline": timeline,
        "event_sequence": events,
        "claims": claims,
        "claim_validation": validated,
        "contradictions": contradictions,
        "communication_graph": graph,
        "narrative_confidence": confidence,
        "court_lawyer_ready_narrative": narrative,
        "dossier_auto_story_layer": {
            "status": "ready_for_review" if events else "insufficient_events",
            "summary": narrative["plain_text"][:1200],
            "requires_human_review": True,
        },
    }


if __name__ == "__main__":
    print(json.dumps(story_reconstruction_payload(), indent=2, sort_keys=True))
