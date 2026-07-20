from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ScopeStatus(StrEnum):
    IN_SCOPE = "in_scope"
    RELOCATION_CONTEXT = "relocation_context"
    OUT_OF_SCOPE = "out_of_scope"
    CANDIDATE_REVIEW_REQUIRED = "candidate_review_required"


INCLUDED_ADDRESS_TERMS = (
    "46 montreal street",
    "46 montreal st",
    "46 montreal",
    "46 montréal",
    "46monst",
)

UNIT_CONTEXT_TERMS = (
    "apt b",
    "apartment b",
    "b-46 montreal",
    "room 3",
)

EXCLUDED_ADDRESS_TERMS = (
    "71 cowdy",
    "71 cowdy street",
    "81 cowdy",
    "cowdy street",
)

RELOCATION_CONTEXT_TERMS = (
    "559 macdonnel",
    "suitable relocation",
    "mitigation",
    "housing continuity",
)

DIRECT_RELEVANCE_TERMS = (
    "46 montreal",
    "46 montreal street",
    "46monst",
    "property standards",
    "building services",
    "kingston fire",
    "electrical safety authority",
    "office of the fire marshal",
    "landlord and tenant board",
    "order to comply",
    "order to remedy",
    "fire inspection",
    "lockout",
    "access",
    "inspection",
    "repair",
    "maintenance",
    "rent return",
    "returned rent",
)


@dataclass(frozen=True)
class ScopeDecision:
    status: ScopeStatus
    reason: str
    matched_terms: tuple[str, ...]


def _normalize(value: str | None) -> str:
    return " ".join(str(value or "").lower().split())


def _matches(text: str, terms: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(term for term in terms if term in text)


def evaluate_text_scope(text: str | None) -> ScopeDecision:
    """Classify text against the 46 Montreal case scope.

    This helper is deliberately conservative. It accepts direct 46 Montreal
    references, treats 559 Macdonnel as relocation/mitigation context, rejects
    Cowdy issue expansion, and otherwise requires human review before entity
    expansion.
    """

    normalized = _normalize(text)
    if not normalized:
        return ScopeDecision(
            ScopeStatus.CANDIDATE_REVIEW_REQUIRED,
            "No text supplied; human review required before scope expansion.",
            (),
        )

    excluded = _matches(normalized, EXCLUDED_ADDRESS_TERMS)
    included = _matches(normalized, INCLUDED_ADDRESS_TERMS)
    relocation = _matches(normalized, RELOCATION_CONTEXT_TERMS)
    direct = _matches(normalized, DIRECT_RELEVANCE_TERMS)

    if excluded and not included:
        return ScopeDecision(
            ScopeStatus.OUT_OF_SCOPE,
            "Cowdy-related reference without direct 46 Montreal scope anchor.",
            excluded,
        )

    if relocation and not included:
        return ScopeDecision(
            ScopeStatus.RELOCATION_CONTEXT,
            "559 Macdonnel or relocation context is mitigation-only, not an issue address.",
            relocation,
        )

    if included or direct:
        return ScopeDecision(
            ScopeStatus.IN_SCOPE,
            "Directly related to the 46 Montreal matter.",
            included + direct,
        )

    return ScopeDecision(
        ScopeStatus.CANDIDATE_REVIEW_REQUIRED,
        "No direct 46 Montreal anchor found; candidate entity review required.",
        (),
    )


def assert_export_allowed(text: str | None) -> ScopeDecision:
    """Return a decision and raise when content is clearly out of scope."""

    decision = evaluate_text_scope(text)
    if decision.status == ScopeStatus.OUT_OF_SCOPE:
        raise ValueError(decision.reason)
    return decision
