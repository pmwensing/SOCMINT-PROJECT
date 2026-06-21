from __future__ import annotations

from dataclasses import dataclass
from typing import Any

SCHEMA = "socmint.dossier_readiness.v13_4"

STATE_BLOCKED = "blocked"
STATE_NEEDS_REVIEW = "needs_review"
STATE_DRAFT_READY = "draft_ready"
STATE_FINAL_READY = "final_ready"
STATE_EXPORTED = "exported"


@dataclass(frozen=True)
class ReadinessInput:
    subject_id: int | None = None
    subject_exists: bool = False
    seed_count: int = 0
    finding_count: int = 0
    report_count: int = 0
    pending_review_count: int = 0
    promoted_claim_without_evidence_count: int = 0
    hash_mismatch_count: int = 0
    unresolved_contradiction_count: int = 0


def _append_if(rows: list[str], condition: bool, message: str) -> None:
    if condition:
        rows.append(message)


def compute_dossier_readiness(data: ReadinessInput | dict[str, Any]) -> dict[str, Any]:
    if isinstance(data, dict):
        data = ReadinessInput(**data)

    blockers: list[str] = []
    warnings: list[str] = []
    next_actions: list[dict[str, str]] = []

    _append_if(blockers, not data.subject_exists, "Create or select a subject.")
    _append_if(blockers, data.seed_count <= 0, "Add at least one seed or target.")
    _append_if(
        blockers, data.hash_mismatch_count > 0, "Resolve evidence hash mismatches."
    )

    _append_if(
        warnings,
        data.finding_count <= 0,
        "Run or import collection to create findings.",
    )
    _append_if(
        warnings,
        data.pending_review_count > 0,
        "Review pending findings before final export.",
    )
    _append_if(
        warnings,
        data.promoted_claim_without_evidence_count > 0,
        "Link evidence to promoted claims before final export.",
    )
    _append_if(
        warnings,
        data.unresolved_contradiction_count > 0,
        "Resolve or explain unresolved contradictions before final export.",
    )

    if not data.subject_exists:
        state = STATE_BLOCKED
        label = "No subject selected"
        next_actions.append(
            {
                "key": "create_subject",
                "label": "Create or open a subject",
                "href": "/spine",
            }
        )
    elif data.seed_count <= 0:
        state = STATE_BLOCKED
        label = "Needs seed intake"
        next_actions.append(
            {"key": "add_seed", "label": "Add seed or target", "href": "/targets"}
        )
    elif data.hash_mismatch_count > 0:
        state = STATE_BLOCKED
        label = "Evidence integrity issue"
        next_actions.append(
            {
                "key": "fix_hashes",
                "label": "Open evidence integrity",
                "href": "/evidence/integrity/gate",
            }
        )
    elif data.report_count > 0:
        state = STATE_EXPORTED
        label = "Dossier export exists"
        next_actions.append(
            {
                "key": "export_package",
                "label": "Open export center",
                "href": "/reports/export-center",
            }
        )
    elif data.finding_count <= 0:
        state = STATE_NEEDS_REVIEW
        label = "Needs collection"
        next_actions.append(
            {
                "key": "run_collection",
                "label": "Run or import collection",
                "href": "/targets",
            }
        )
    elif (
        data.pending_review_count > 0
        or data.promoted_claim_without_evidence_count > 0
        or data.unresolved_contradiction_count > 0
    ):
        state = STATE_NEEDS_REVIEW
        label = "Needs analyst review"
        next_actions.append(
            {
                "key": "review_findings",
                "label": "Open enrichment review",
                "href": "/spine/enrichment-review",
            }
        )
    else:
        state = STATE_DRAFT_READY
        label = "Draft dossier ready"
        next_actions.append(
            {
                "key": "generate_dossier",
                "label": "Generate dossier",
                "href": f"/spine/subjects/{data.subject_id}/full-report",
            }
        )

    final_export_allowed = state in {STATE_FINAL_READY, STATE_EXPORTED}
    draft_export_allowed = state in {
        STATE_DRAFT_READY,
        STATE_FINAL_READY,
        STATE_EXPORTED,
    }

    return {
        "schema": SCHEMA,
        "subject_id": data.subject_id,
        "state": state,
        "label": label,
        "blockers": blockers,
        "warnings": warnings,
        "next_actions": next_actions,
        "draft_export_allowed": draft_export_allowed,
        "final_export_allowed": final_export_allowed,
        "counts": {
            "seed_count": data.seed_count,
            "finding_count": data.finding_count,
            "report_count": data.report_count,
            "pending_review_count": data.pending_review_count,
            "promoted_claim_without_evidence_count": data.promoted_claim_without_evidence_count,
            "hash_mismatch_count": data.hash_mismatch_count,
            "unresolved_contradiction_count": data.unresolved_contradiction_count,
        },
    }
