from __future__ import annotations

from typing import Any

from .case_import_pilot_v37_3 import (
    current_review_decisions,
    current_scope_assessments,
)
from .entity_accuracy_workspace_v36_8 import build_entity_accuracy_workspace
from .import_observation_promotion_v37_4 import current_promotions
from .operational_import_record_projection_v37_2 import (
    current_staged_record_projections,
)
from .operational_import_v37_1 import current_imports

SCHEMA = "socmint.guided_analyst_workflow.v37_5"
VERSION = "v37.5.0"


def _finding(
    key: str,
    severity: str,
    count: int,
    message: str,
    next_action: str,
) -> dict[str, Any]:
    return {
        "key": key,
        "severity": severity,
        "count": count,
        "message": message,
        "next_action": next_action,
    }


def build_guided_analyst_workflow() -> dict[str, Any]:
    imports = current_imports()
    records = current_staged_record_projections()
    assessments = current_scope_assessments()
    decisions = current_review_decisions()
    promotions = current_promotions()
    entity_accuracy = build_entity_accuracy_workspace()

    assessment_by_record = {
        str(item.get("staged_record_id") or ""): item
        for item in assessments
        if item.get("staged_record_id")
    }
    decision_by_record = {
        str(item.get("staged_record_id") or ""): item
        for item in decisions
        if item.get("staged_record_id")
    }
    promotion_by_record = {
        str(item.get("staged_record_id") or ""): item
        for item in promotions
        if item.get("staged_record_id")
    }

    unassessed = [
        item
        for item in records
        if str(item.get("staged_record_id") or "") not in assessment_by_record
    ]
    waiting_review = [
        item
        for item in records
        if str(item.get("staged_record_id") or "") in assessment_by_record
        and str(item.get("staged_record_id") or "") not in decision_by_record
    ]
    quarantined = [item for item in records if item.get("initial_state") == "quarantined"]
    duplicates = [item for item in records if item.get("initial_state") == "duplicate"]
    candidate_records = [
        item
        for item in assessments
        if item.get("candidate_review_required") is True
        and str(item.get("staged_record_id") or "") not in decision_by_record
    ]
    accepted_not_promoted = [
        decision
        for decision in decisions
        if decision.get("decision") == "accepted"
        and decision.get("observation_promotion_allowed") is True
        and str(decision.get("staged_record_id") or "") not in promotion_by_record
    ]
    relocation_promotions = [
        item for item in promotions if item.get("relocation_context_only") is True
    ]

    findings: list[dict[str, Any]] = []
    if unassessed:
        findings.append(
            _finding(
                "import_records_waiting_scope_assessment",
                "attention",
                len(unassessed),
                "Staged import records still require case-scope assessment.",
                "Assess each record against the case scope.",
            )
        )
    if waiting_review:
        findings.append(
            _finding(
                "import_records_waiting_human_review",
                "attention",
                len(waiting_review),
                "Scope-assessed records still require an explicit human decision.",
                "Record accepted, quarantined, or rejected decisions.",
            )
        )
    if quarantined:
        findings.append(
            _finding(
                "quarantined_import_records",
                "integrity_alert",
                len(quarantined),
                "Quarantined records cannot support claims or be promoted without resolution.",
                "Resolve or reject each quarantine finding.",
            )
        )
    if duplicates:
        findings.append(
            _finding(
                "duplicate_import_records",
                "integrity_alert",
                len(duplicates),
                "Duplicate records are retained but cannot inflate observation or claim support.",
                "Reject duplicates while preserving their dependency record.",
            )
        )
    if candidate_records:
        findings.append(
            _finding(
                "candidate_entities_waiting_resolution",
                "attention",
                len(candidate_records),
                "Unanchored entity references require a reviewed candidate-resolution decision.",
                "Resolve the candidate without automatically merging identities.",
            )
        )
    if accepted_not_promoted:
        findings.append(
            _finding(
                "accepted_records_waiting_observation_promotion",
                "attention",
                len(accepted_not_promoted),
                "Accepted records have not been explicitly promoted into v29 observations.",
                "Promote only the intended record, one at a time.",
            )
        )
    if relocation_promotions:
        findings.append(
            _finding(
                "relocation_context_separated_from_issue_support",
                "informational",
                len(relocation_promotions),
                "Relocation observations are preserved but remain barred from issue-claim support.",
                "Retain the contextual classification in chronology and dossier review.",
            )
        )

    entity_findings = entity_accuracy.get("findings") or []
    if isinstance(entity_findings, list):
        findings.extend(
            {**item, "source_workspace": "entity_accuracy_v36_8"}
            for item in entity_findings
            if isinstance(item, dict)
        )

    summary = {
        "import_count": len(imports),
        "staged_record_count": len(records),
        "scope_assessment_count": len(assessments),
        "review_decision_count": len(decisions),
        "observation_promotion_count": len(promotions),
        "entity_candidate_count": int(
            (entity_accuracy.get("summary") or {}).get("entity_candidate_count") or 0
        ),
        "claim_verification_count": int(
            (entity_accuracy.get("summary") or {}).get("claim_verification_count") or 0
        ),
        "relationship_timeline_count": int(
            (entity_accuracy.get("summary") or {}).get("relationship_timeline_count") or 0
        ),
        "dossier_snapshot_count": int(
            (entity_accuracy.get("summary") or {}).get("dossier_snapshot_count") or 0
        ),
        "finding_count": len(findings),
    }
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "ready",
        "read_only": True,
        "summary": summary,
        "import_inventory": imports,
        "staged_record_inventory": records,
        "scope_assessment_inventory": assessments,
        "review_decision_inventory": decisions,
        "observation_promotion_inventory": promotions,
        "entity_accuracy_workspace": entity_accuracy,
        "findings": findings,
        "controls": {
            "automatic_collection": False,
            "automatic_observation_promotion": False,
            "automatic_entity_merge": False,
            "automatic_claim_approval": False,
            "automatic_dossier_mutation": False,
            "automatic_export": False,
            "automatic_publication": False,
            "human_review_gate": "v30.5",
            "dossier_contribution_gate": "v30.6",
            "write_actions_exposed_by_workflow": [],
        },
    }
