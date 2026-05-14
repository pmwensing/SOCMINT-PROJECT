from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime
from typing import Any

IDENTITY_CONFIDENCE_SCHEMA = "socmint.v7_5.identity_confidence"
CLAIM_SECTIONS = ["accounts", "evidence_backed_attributes", "relationships"]


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _as_float(value: Any, default: float = 0.5) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        result = default
    return max(0.0, min(1.0, result))


def _evidence_refs(item: dict[str, Any]) -> list[str]:
    refs = item.get("evidence_refs") or item.get("evidence_ids") or []
    if not isinstance(refs, list):
        refs = [refs]
    for key in ("evidence_id", "artifact_id", "source_ref"):
        value = item.get(key)
        if value not in (None, ""):
            refs.append(value)
    return list(dict.fromkeys(str(ref) for ref in refs if ref not in (None, "")))


def _claim_key(section: str, item: dict[str, Any]) -> str:
    if section == "accounts":
        return f"account:{item.get('platform') or 'unknown'}:{item.get('handle') or item.get('url') or item.get('id') or ''}"
    if section == "relationships":
        return f"relationship:{item.get('target') or ''}:{item.get('relationship') or ''}"
    return f"attribute:{item.get('name') or item.get('claim') or item.get('attribute') or 'unknown'}:{item.get('value') or ''}"


def _claim_label(section: str, item: dict[str, Any]) -> str:
    return str(
        item.get("name")
        or item.get("claim")
        or item.get("attribute")
        or item.get("handle")
        or item.get("url")
        or item.get("target")
        or item.get("relationship")
        or item.get("id")
        or section
    )


def _iter_claims(payload: dict[str, Any]):
    for section in CLAIM_SECTIONS:
        rows = payload.get(section) or []
        if not isinstance(rows, list):
            continue
        for index, item in enumerate(rows):
            if isinstance(item, dict):
                yield section, index, item


def confidence_bucket(score: float) -> str:
    if score >= 0.9:
        return "strong"
    if score >= 0.7:
        return "high"
    if score >= 0.4:
        return "medium"
    return "low"


def explain_claim_confidence(section: str, index: int, item: dict[str, Any]) -> dict[str, Any]:
    base = _as_float(item.get("confidence"), default=0.5)
    refs = _evidence_refs(item)
    evidence_bonus = min(0.2, len(refs) * 0.05)
    source_bonus = 0.05 if item.get("source") or item.get("source_url") or item.get("platform") else 0.0
    review_bonus = 0.05 if item.get("validation_state") in {"promoted", "verified", "reviewed"} else 0.0
    contradiction_penalty = 0.25 if item.get("status") in {"conflict", "contradicted"} else 0.0
    final_score = max(0.0, min(1.0, base + evidence_bonus + source_bonus + review_bonus - contradiction_penalty))
    return {
        "section": section,
        "index": index,
        "claim_key": _claim_key(section, item),
        "claim": _claim_label(section, item),
        "base_confidence": round(base, 3),
        "evidence_count": len(refs),
        "source_present": bool(item.get("source") or item.get("source_url") or item.get("platform")),
        "review_state": item.get("validation_state") or item.get("review_state") or item.get("status"),
        "contradiction_penalty": contradiction_penalty,
        "score": round(final_score, 3),
        "bucket": confidence_bucket(final_score),
        "evidence_refs": refs,
    }


def find_contradictions(payload: dict[str, Any]) -> list[dict[str, Any]]:
    values_by_name: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for index, item in enumerate(payload.get("evidence_backed_attributes") or []):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("claim") or item.get("attribute") or "").strip()
        value = str(item.get("value") or "").strip()
        if not name or not value:
            continue
        values_by_name[name][value].append({"index": index, "evidence_refs": _evidence_refs(item), "confidence": item.get("confidence")})

    conflicts = []
    for name, values in sorted(values_by_name.items()):
        if len(values) <= 1:
            continue
        conflicts.append(
            {
                "claim": name,
                "values": sorted(values),
                "status": "contradicted",
                "support": {value: refs for value, refs in sorted(values.items())},
            }
        )
    return conflicts


def build_identity_confidence_report(payload: dict[str, Any]) -> dict[str, Any]:
    explanations = [explain_claim_confidence(section, index, item) for section, index, item in _iter_claims(payload)]
    contradictions = find_contradictions(payload)
    bucket_counts = Counter(item["bucket"] for item in explanations)
    low_confidence = [item for item in explanations if item["bucket"] == "low"]
    needs_review = [item for item in explanations if item["bucket"] in {"low", "medium"} or item["contradiction_penalty"] > 0]
    status = "fail" if contradictions else "warn" if needs_review else "pass"
    return {
        "schema": IDENTITY_CONFIDENCE_SCHEMA,
        "generated_at": utc_now(),
        "approved_line": "v7.5",
        "status": status,
        "claim_count": len(explanations),
        "bucket_counts": dict(sorted(bucket_counts.items())),
        "low_confidence_count": len(low_confidence),
        "needs_review_count": len(needs_review),
        "contradiction_count": len(contradictions),
        "confidence_explanations": explanations,
        "contradictions": contradictions,
        "needs_review": needs_review,
    }


def attach_identity_confidence(payload: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(payload)
    enriched["identity_confidence"] = build_identity_confidence_report(payload)
    return enriched
