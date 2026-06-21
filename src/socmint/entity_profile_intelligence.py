from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Any

from .dossier_builder_v3 import build_dossier_payload
from .dossier_builder_v3 import clamp_confidence
from .dossier_quality_v7_5 import evaluate_dossier_quality

ENTITY_PROFILE_INTELLIGENCE_SCHEMA = "socmint.entity_profile_intelligence.v10_20_0"


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _first(*values: Any, default: Any = None) -> Any:
    for value in values:
        if value not in (None, "", []):
            return value
    return default


def _evidence_refs(item: dict[str, Any]) -> list[str]:
    refs = item.get("evidence_refs") or item.get("evidence_ids") or []
    if refs:
        return list(refs)
    evidence_id = item.get("evidence_id")
    return [evidence_id] if evidence_id else []


def _sort_timeline(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def key(event: dict[str, Any]) -> tuple[int, str]:
        value = str(event.get("date") or event.get("timestamp") or "")
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
            return (0, value)
        except ValueError:
            return (1, value)

    return sorted(events, key=key)


def identity_section(
    subject: dict[str, Any], evidence: list[dict[str, Any]]
) -> dict[str, Any]:
    aliases = list(
        dict.fromkeys(
            _list(subject.get("aliases"))
            + [item.get("alias") for item in evidence if item.get("alias")]
        )
    )
    handles = list(
        dict.fromkeys(
            _list(subject.get("handles"))
            + [item.get("handle") for item in evidence if item.get("handle")]
        )
    )
    platforms = sorted(
        {item.get("platform") for item in evidence if item.get("platform")}
    )
    return {
        "primary_name": _first(
            subject.get("display_name"), subject.get("name"), default="Unknown subject"
        ),
        "subject_id": subject.get("subject_id"),
        "case_id": subject.get("case_id"),
        "aliases": aliases,
        "handles": handles,
        "platforms": platforms,
        "evidence_refs": [
            item.get("evidence_id") for item in evidence if item.get("evidence_id")
        ],
    }


def account_section(
    subject: dict[str, Any], evidence: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    accounts = []
    for account in _list(subject.get("accounts")):
        accounts.append({**account, "evidence_refs": _evidence_refs(account)})
    for item in evidence:
        if item.get("account") or item.get("platform") or item.get("handle"):
            accounts.append(
                {
                    "platform": item.get("platform") or item.get("source"),
                    "handle": item.get("handle") or item.get("account"),
                    "url": item.get("url"),
                    "confidence": clamp_confidence(item.get("confidence", 0.5)),
                    "evidence_refs": _evidence_refs(item),
                }
            )
    seen = set()
    unique = []
    for account in accounts:
        key = (account.get("platform"), account.get("handle"), account.get("url"))
        if key not in seen:
            seen.add(key)
            unique.append(account)
    return unique


def attribute_section(
    subject: dict[str, Any], evidence: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    attributes = []
    for item in _list(subject.get("attributes")):
        attributes.append({**item, "evidence_refs": _evidence_refs(item)})
    for item in evidence:
        if item.get("attribute") or item.get("claim"):
            attributes.append(
                {
                    "name": item.get("attribute") or item.get("claim"),
                    "value": item.get("value") or item.get("label"),
                    "source": item.get("source"),
                    "confidence": clamp_confidence(item.get("confidence", 0.5)),
                    "evidence_refs": _evidence_refs(item),
                }
            )
    return attributes


def timeline_section(
    subject: dict[str, Any], evidence: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    events = []
    for event in _list(subject.get("timeline")):
        events.append({**event, "evidence_refs": _evidence_refs(event)})
    for item in evidence:
        if item.get("date") or item.get("timestamp"):
            events.append(
                {
                    "date": item.get("date") or item.get("timestamp"),
                    "event": item.get("event") or item.get("label"),
                    "source": item.get("source"),
                    "confidence": clamp_confidence(item.get("confidence", 0.5)),
                    "evidence_refs": _evidence_refs(item),
                }
            )
    return _sort_timeline(events)


def relationship_section(
    subject: dict[str, Any], evidence: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    relationships = []
    for rel in _list(subject.get("relationships")):
        relationships.append({**rel, "evidence_refs": _evidence_refs(rel)})
    for item in evidence:
        if item.get("related_entity") or item.get("relationship"):
            relationships.append(
                {
                    "target": item.get("related_entity") or item.get("target"),
                    "relationship": item.get("relationship") or item.get("relation"),
                    "source": item.get("source"),
                    "confidence": clamp_confidence(item.get("confidence", 0.5)),
                    "evidence_refs": _evidence_refs(item),
                }
            )
    return relationships


def contradiction_section(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_claim: dict[str, set[str]] = defaultdict(set)
    refs: dict[str, list[str]] = defaultdict(list)
    for item in evidence:
        claim = item.get("attribute") or item.get("claim")
        if not claim:
            continue
        value = str(item.get("value") or item.get("label") or "")
        by_claim[str(claim)].add(value)
        if item.get("evidence_id"):
            refs[str(claim)].append(item["evidence_id"])
    return [
        {
            "claim": claim,
            "values": sorted(values),
            "evidence_refs": refs[claim],
            "status": "conflict",
        }
        for claim, values in sorted(by_claim.items())
        if len(values) > 1
    ]


def risk_section(
    evidence: list[dict[str, Any]], contradictions: list[dict[str, Any]]
) -> dict[str, Any]:
    low_conf = sum(
        1 for item in evidence if clamp_confidence(item.get("confidence", 0.5)) < 0.7
    )
    source_counts = Counter(
        item.get("source") for item in evidence if item.get("source")
    )
    score = min(1.0, (low_conf * 0.15) + (len(contradictions) * 0.25))
    return {
        "risk_score": round(score, 3),
        "risk_level": "high" if score >= 0.7 else "medium" if score >= 0.35 else "low",
        "low_confidence_items": low_conf,
        "contradiction_count": len(contradictions),
        "source_counts": dict(source_counts),
    }


def build_entity_profile_intelligence(
    subject: dict[str, Any],
    evidence: list[dict[str, Any]] | None = None,
    analyst_reviewed: bool = False,
    analyst_notes: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    evidence = evidence or []
    base = build_dossier_payload(
        subject, evidence=evidence, analyst_reviewed=analyst_reviewed
    )
    contradictions = contradiction_section(evidence)
    payload = {
        "schema": ENTITY_PROFILE_INTELLIGENCE_SCHEMA,
        "subject": base["subject"],
        "identity_summary": identity_section(subject, evidence),
        "accounts": account_section(subject, evidence),
        "evidence_backed_attributes": attribute_section(subject, evidence),
        "timeline": timeline_section(subject, evidence),
        "relationships": relationship_section(subject, evidence),
        "contradictions": contradictions,
        "risk_scoring": risk_section(evidence, contradictions),
        "confidence_scoring": base["confidence_scoring"],
        "source_citations": base["source_traceability"],
        "analyst_notes": analyst_notes or _list(subject.get("analyst_notes")),
        "review_queue": base["review_queue"],
        "export_preflight": base["export_preflight"],
    }
    payload["sections"] = [
        "identity_summary",
        "accounts",
        "evidence_backed_attributes",
        "timeline",
        "relationships",
        "contradictions",
        "risk_scoring",
        "confidence_scoring",
        "source_citations",
        "analyst_notes",
    ]
    payload["quality_gate"] = evaluate_dossier_quality(payload)
    payload["export_ready"] = payload["quality_gate"]["status"] == "pass"
    return payload


def _summary_export_ready(payload: dict[str, Any]) -> Any:
    preflight = payload.get("export_preflight") or {}
    if isinstance(preflight, dict) and "ready" in preflight:
        return preflight.get("ready")
    return payload.get("export_ready")


def entity_profile_intelligence_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": ENTITY_PROFILE_INTELLIGENCE_SCHEMA,
        "subject_id": payload.get("subject", {}).get("subject_id"),
        "case_id": payload.get("subject", {}).get("case_id"),
        "account_count": len(payload.get("accounts", [])),
        "attribute_count": len(payload.get("evidence_backed_attributes", [])),
        "timeline_event_count": len(payload.get("timeline", [])),
        "relationship_count": len(payload.get("relationships", [])),
        "contradiction_count": len(payload.get("contradictions", [])),
        "risk_level": payload.get("risk_scoring", {}).get("risk_level"),
        "confidence": payload.get("confidence_scoring", {}).get("score"),
        "export_ready": _summary_export_ready(payload),
        "quality_status": payload.get("quality_gate", {}).get("status"),
        "quality_finding_count": payload.get("quality_gate", {}).get("finding_count"),
    }


def entity_profile_intelligence_markdown(payload: dict[str, Any]) -> str:
    subject = payload.get("subject", {})
    lines = [
        f"# Entity Profile Dossier — {subject.get('display_name')}",
        "",
        f"Subject ID: {subject.get('subject_id')}",
        f"Case ID: {subject.get('case_id')}",
        f"Confidence: {payload.get('confidence_scoring', {}).get('score')}",
        f"Risk: {payload.get('risk_scoring', {}).get('risk_level')}",
        f"Quality Gate: {payload.get('quality_gate', {}).get('status', 'not_checked')}",
        "",
        "## Aliases / Handles",
    ]
    identity = payload.get("identity_summary", {})
    lines.append(f"Aliases: {', '.join(identity.get('aliases', [])) or 'none'}")
    lines.append(f"Handles: {', '.join(identity.get('handles', [])) or 'none'}")
    lines.extend(["", "## Accounts"])
    for account in payload.get("accounts", []):
        lines.append(
            f"- {account.get('platform')}: {account.get('handle') or account.get('url')} [{', '.join(account.get('evidence_refs', []))}]"
        )
    lines.extend(["", "## Evidence-backed Attributes"])
    for attr in payload.get("evidence_backed_attributes", []):
        lines.append(
            f"- {attr.get('name')}: {attr.get('value')} [{', '.join(attr.get('evidence_refs', []))}]"
        )
    lines.extend(["", "## Timeline"])
    for event in payload.get("timeline", []):
        lines.append(
            f"- {event.get('date')}: {event.get('event')} [{', '.join(event.get('evidence_refs', []))}]"
        )
    lines.extend(["", "## Relationships"])
    for rel in payload.get("relationships", []):
        lines.append(
            f"- {rel.get('target')}: {rel.get('relationship')} [{', '.join(rel.get('evidence_refs', []))}]"
        )
    lines.extend(["", "## Contradictions"])
    for conflict in payload.get("contradictions", []):
        lines.append(
            f"- {conflict.get('claim')}: {', '.join(conflict.get('values', []))} [{', '.join(conflict.get('evidence_refs', []))}]"
        )
    if not payload.get("contradictions"):
        lines.append("- none")
    quality = payload.get("quality_gate") or {}
    lines.extend(["", "## Quality Gate"])
    lines.append(f"- Status: {quality.get('status', 'not_checked')}")
    lines.append(f"- Findings: {quality.get('finding_count', 0)}")
    return "\n".join(lines) + "\n"
