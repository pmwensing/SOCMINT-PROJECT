from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .integrity_gate_v12_7_1 import evidence_integrity_summary, integrity_drilldown_for_claims
from .narrative_export_v12_6_1 import narrative_dashboard_polish_payload

try:
    from .spine_intelligence_v11_9 import spine_intelligence_payload
except Exception:  # pragma: no cover
    spine_intelligence_payload = None

SCHEMA = "socmint.assertion_trust.v12_8"
DASHBOARD_SCHEMA = "socmint.corroboration_dashboard.v12_8"


@dataclass
class AssertionSource:
    source_type: str
    source_id: str | None
    label: str
    confidence: float = 0.5
    status: str = "review"
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TrustedAssertion:
    assertion_id: str
    subject: str
    predicate: str
    value: str
    evidence_id: str | None
    sources: list[AssertionSource]
    contradiction_state: str
    analyst_state: str
    integrity_state: str
    trust_score: float
    trust_rating: str
    release_state: str
    reasoning: list[str]

    def as_dict(self) -> dict[str, Any]:
        row = asdict(self)
        row["sources"] = [source.as_dict() if hasattr(source, "as_dict") else source for source in self.sources]
        return row


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _rating(score: float) -> str:
    if score >= 0.85:
        return "strong"
    if score >= 0.7:
        return "supported"
    if score >= 0.5:
        return "review"
    if score >= 0.3:
        return "weak"
    return "unsupported"


def _release_state(score: float, contradiction_state: str, integrity_state: str, analyst_state: str) -> str:
    if contradiction_state == "contradicted" or integrity_state == "hold":
        return "hold"
    if analyst_state == "rejected":
        return "hold"
    if score >= 0.8 and analyst_state in {"confirmed", "reviewed"} and integrity_state in {"usable", "review", "unknown"}:
        return "dossier-ready"
    if score >= 0.6:
        return "analyst-review"
    return "low-confidence"


def _claim_key(claim: dict[str, Any]) -> tuple[str, str, str, str | None]:
    return (
        str(claim.get("subject") or "case"),
        str(claim.get("predicate") or "unknown"),
        str(claim.get("value") or ""),
        claim.get("evidence_id"),
    )


def _connector_sources(subject_id: int | None = None) -> list[AssertionSource]:
    if subject_id is None or spine_intelligence_payload is None:
        return []
    sources: list[AssertionSource] = []
    try:
        payload = spine_intelligence_payload(subject_id)
    except Exception:
        return []
    for run in payload.get("runs", []):
        badge = run.get("badge") or "review"
        status = run.get("status") or "unknown"
        confidence = 0.82 if badge == "real" or run.get("real_observation_count", 0) else 0.35 if status == "dry_run" else 0.45 if status in {"failed", "timeout"} else 0.55
        sources.append(AssertionSource(
            source_type="connector_run",
            source_id=str(run.get("id")) if run.get("id") is not None else None,
            label=str(run.get("connector") or "connector"),
            confidence=confidence,
            status=badge if badge != "diagnostic" else "dry-run",
            details=run,
        ))
    return sources


def _contradiction_index(polish: dict[str, Any]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    issues: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    base = polish.get("base_story", {})
    for issue in base.get("contradictions", {}).get("contradictions", []):
        issues[(str(issue.get("subject")), str(issue.get("predicate")))].append(issue)
    return issues


def _integrity_by_evidence(root: str | None = None) -> dict[str, dict[str, Any]]:
    summary = evidence_integrity_summary(root=root)
    return {str(row.get("evidence_id")): row for row in summary.get("item_decisions", []) if row.get("evidence_id")}


def _analyst_state(claim: dict[str, Any]) -> str:
    if claim.get("maturity") == "court-grade":
        return "reviewed"
    if claim.get("validated") is True:
        return "reviewed"
    if str(claim.get("polarity") or "") == "rejected":
        return "rejected"
    if str(claim.get("polarity") or "") == "confirmed":
        return "confirmed"
    return "unreviewed"


def _score_assertion(claim: dict[str, Any], sources: list[AssertionSource], contradiction_state: str, integrity_state: str, analyst_state: str) -> tuple[float, list[str]]:
    reasoning: list[str] = []
    base = float(claim.get("confidence") or 0.5) * 0.35
    reasoning.append(f"claim_confidence_component={base:.2f}")
    source_component = 0.0
    if sources:
        unique_types = len({source.source_type for source in sources})
        avg_source = sum(source.confidence for source in sources) / len(sources)
        source_component = min(0.3, avg_source * 0.18 + min(0.12, unique_types * 0.04))
        reasoning.append(f"source_component={source_component:.2f}; sources={len(sources)}; unique_types={unique_types}")
    else:
        reasoning.append("source_component=0.00; no corroborating sources")
    integrity_component = {"usable": 0.2, "review": 0.11, "unknown": 0.06, "hold": -0.25}.get(integrity_state, 0.04)
    reasoning.append(f"integrity_component={integrity_component:.2f}; state={integrity_state}")
    analyst_component = {"confirmed": 0.18, "reviewed": 0.12, "unreviewed": 0.0, "rejected": -0.35}.get(analyst_state, 0.0)
    reasoning.append(f"analyst_component={analyst_component:.2f}; state={analyst_state}")
    contradiction_penalty = -0.3 if contradiction_state == "contradicted" else -0.08 if contradiction_state == "review" else 0.04
    reasoning.append(f"contradiction_component={contradiction_penalty:.2f}; state={contradiction_state}")
    score = max(0.0, min(1.0, base + source_component + integrity_component + analyst_component + contradiction_penalty))
    return round(score, 3), reasoning


def build_assertion_trust(subject_id: int | None = None, root: str | None = None) -> dict[str, Any]:
    polish = narrative_dashboard_polish_payload(subject_id=subject_id, root=root)
    claims_by_evidence = polish.get("claims_by_evidence", {})
    integrity = _integrity_by_evidence(root=root)
    contradiction_index = _contradiction_index(polish)
    connector_sources = _connector_sources(subject_id)
    assertions: list[TrustedAssertion] = []
    seen = set()
    for evidence_id, claims in claims_by_evidence.items():
        evidence_integrity = integrity.get(str(evidence_id), {"usable_state": "unknown", "composite_score": 0})
        integrity_state = evidence_integrity.get("usable_state", "unknown")
        for claim in claims:
            key = _claim_key(claim)
            if key in seen:
                continue
            seen.add(key)
            contradiction_state = "contradicted" if (str(claim.get("subject")), str(claim.get("predicate"))) in contradiction_index else "clear"
            analyst_state = _analyst_state(claim)
            sources = [
                AssertionSource(
                    source_type="narrative_claim",
                    source_id=str(claim.get("claim_id")),
                    label=f"{claim.get('predicate')}={claim.get('value')}",
                    confidence=float(claim.get("confidence") or 0.5),
                    status=str(claim.get("maturity") or "review"),
                    details=claim,
                ),
                AssertionSource(
                    source_type="forensic_evidence",
                    source_id=str(evidence_id),
                    label=str(evidence_integrity.get("filename") or evidence_id),
                    confidence=float(evidence_integrity.get("composite_score") or 0.0),
                    status=str(integrity_state),
                    details=evidence_integrity,
                ),
            ]
            sources.extend(connector_sources[:5])
            score, reasoning = _score_assertion(claim, sources, contradiction_state, integrity_state, analyst_state)
            assertions.append(TrustedAssertion(
                assertion_id=f"asrt-{len(assertions)+1:04d}",
                subject=str(claim.get("subject") or "case"),
                predicate=str(claim.get("predicate") or "unknown"),
                value=str(claim.get("value") or ""),
                evidence_id=str(evidence_id) if evidence_id else None,
                sources=sources,
                contradiction_state=contradiction_state,
                analyst_state=analyst_state,
                integrity_state=str(integrity_state),
                trust_score=score,
                trust_rating=_rating(score),
                release_state=_release_state(score, contradiction_state, str(integrity_state), analyst_state),
                reasoning=reasoning,
            ))
    assertions.sort(key=lambda item: item.trust_score, reverse=True)
    rows = [item.as_dict() for item in assertions]
    counts = Counter(row["release_state"] for row in rows)
    ratings = Counter(row["trust_rating"] for row in rows)
    return {
        "schema": SCHEMA,
        "generated_at": utc_now(),
        "subject_id": subject_id,
        "assertion_count": len(rows),
        "assertions": rows,
        "summary": {
            "release_states": dict(counts),
            "trust_ratings": dict(ratings),
            "avg_trust_score": round(sum(row["trust_score"] for row in rows) / max(1, len(rows)), 3),
            "dossier_ready": counts.get("dossier-ready", 0),
            "hold": counts.get("hold", 0),
            "analyst_review": counts.get("analyst-review", 0),
        },
        "integrity_drilldown": integrity_drilldown_for_claims(claims_by_evidence, root=root),
    }


def corroboration_dashboard_payload(subject_id: int | None = None, root: str | None = None) -> dict[str, Any]:
    trust = build_assertion_trust(subject_id=subject_id, root=root)
    return {
        "schema": DASHBOARD_SCHEMA,
        "generated_at": utc_now(),
        "subject_id": subject_id,
        "trust": trust,
        "top_assertions": trust.get("assertions", [])[:10],
        "review_queue": [row for row in trust.get("assertions", []) if row.get("release_state") in {"analyst-review", "hold", "low-confidence"}],
        "explanation": "Cross-source corroboration combines connector findings, forensic evidence, integrity scores, narrative claims, analyst validation state, and contradiction status.",
    }


if __name__ == "__main__":
    print(json.dumps(corroboration_dashboard_payload(), indent=2, sort_keys=True))
