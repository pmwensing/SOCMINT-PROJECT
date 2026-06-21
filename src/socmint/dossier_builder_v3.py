from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

DOSSIER_BUILDER_SCHEMA = "socmint.dossier_builder.v10_3_0"

REQUIRED_DOSSIER_SECTIONS = [
    "identity_summary",
    "source_traceability",
    "evidence_matrix",
    "confidence_scoring",
    "review_queue",
    "export_preflight",
]

CONFIDENCE_WEIGHTS = {
    "direct_evidence": 0.35,
    "source_quality": 0.25,
    "corroboration": 0.20,
    "recency": 0.10,
    "analyst_review": 0.10,
}


@dataclass(frozen=True)
class DossierSubject:
    subject_id: str
    display_name: str
    aliases: list[str] = field(default_factory=list)
    case_id: str | None = None


@dataclass(frozen=True)
class EvidenceItem:
    evidence_id: str
    label: str
    source: str
    confidence: float = 0.5
    artifact_id: str | None = None
    notes: str | None = None


def clamp_confidence(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def confidence_score(
    evidence: list[dict[str, Any]] | None = None, analyst_reviewed: bool = False
) -> dict[str, Any]:
    evidence = evidence or []
    direct = 1.0 if any(item.get("artifact_id") for item in evidence) else 0.0
    source_quality = sum(
        clamp_confidence(item.get("confidence", 0.5)) for item in evidence
    ) / max(len(evidence), 1)
    corroboration = min(
        1.0, len({item.get("source") for item in evidence if item.get("source")}) / 3
    )
    recency = 0.75 if evidence else 0.0
    review = 1.0 if analyst_reviewed else 0.0
    components = {
        "direct_evidence": direct,
        "source_quality": source_quality,
        "corroboration": corroboration,
        "recency": recency,
        "analyst_review": review,
    }
    weighted = sum(
        components[key] * weight for key, weight in CONFIDENCE_WEIGHTS.items()
    )
    return {
        "schema": DOSSIER_BUILDER_SCHEMA,
        "score": round(clamp_confidence(weighted), 3),
        "components": components,
        "weights": CONFIDENCE_WEIGHTS,
    }


def build_dossier_payload(
    subject: dict[str, Any],
    evidence: list[dict[str, Any]] | None = None,
    analyst_reviewed: bool = False,
) -> dict[str, Any]:
    evidence = evidence or []
    score = confidence_score(evidence, analyst_reviewed=analyst_reviewed)
    review_items = [
        {
            "evidence_id": item.get("evidence_id"),
            "label": item.get("label"),
            "reason": "low_confidence"
            if clamp_confidence(item.get("confidence", 0.5)) < 0.7
            else "confirm_assertion",
        }
        for item in evidence
        if clamp_confidence(item.get("confidence", 0.5)) < 0.85
    ]
    export_preflight = {
        "ready": analyst_reviewed and bool(evidence) and score["score"] >= 0.65,
        "requires_review": not analyst_reviewed,
        "evidence_count": len(evidence),
        "low_confidence_count": sum(
            1
            for item in evidence
            if clamp_confidence(item.get("confidence", 0.5)) < 0.7
        ),
    }
    return {
        "schema": DOSSIER_BUILDER_SCHEMA,
        "subject": {
            "subject_id": subject.get("subject_id"),
            "display_name": subject.get("display_name")
            or subject.get("name")
            or "Unknown subject",
            "aliases": subject.get("aliases", []),
            "case_id": subject.get("case_id"),
        },
        "sections": REQUIRED_DOSSIER_SECTIONS,
        "identity_summary": {
            "primary_name": subject.get("display_name")
            or subject.get("name")
            or "Unknown subject",
            "alias_count": len(subject.get("aliases", [])),
            "case_scoped": bool(subject.get("case_id")),
        },
        "source_traceability": [
            {
                "evidence_id": item.get("evidence_id"),
                "source": item.get("source"),
                "artifact_id": item.get("artifact_id"),
            }
            for item in evidence
        ],
        "evidence_matrix": evidence,
        "confidence_scoring": score,
        "review_queue": review_items,
        "export_preflight": export_preflight,
    }


def dossier_builder_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": DOSSIER_BUILDER_SCHEMA,
        "subject_id": payload.get("subject", {}).get("subject_id"),
        "case_id": payload.get("subject", {}).get("case_id"),
        "section_count": len(payload.get("sections", [])),
        "evidence_count": len(payload.get("evidence_matrix", [])),
        "confidence": payload.get("confidence_scoring", {}).get("score"),
        "export_ready": payload.get("export_preflight", {}).get("ready"),
        "review_queue_count": len(payload.get("review_queue", [])),
    }


def dossier_builder_capabilities() -> dict[str, Any]:
    return {
        "schema": DOSSIER_BUILDER_SCHEMA,
        "sections": REQUIRED_DOSSIER_SECTIONS,
        "outputs": ["json", "html-ready", "pdf-ready"],
        "controls": [
            "case-scoped subject",
            "source traceability",
            "confidence scoring",
            "analyst review queue",
            "export preflight",
        ],
    }
