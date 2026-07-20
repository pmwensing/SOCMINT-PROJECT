from __future__ import annotations

from typing import Any

from .import_observation_promotion_v37_4 import current_promotions
from .operational_import_record_projection_v37_2 import find_staged_record_projection
from .operational_import_v37_1 import find_import
from .relationship_timeline_v36_6 import current_relationship_assessments

SCHEMA = "socmint.relationship_chronology_workflow.v37_6"
VERSION = "v37.6.0"


def _promotion_entry(promotion: dict[str, Any]) -> dict[str, Any] | None:
    staged_record_id = str(promotion.get("staged_record_id") or "")
    staged = find_staged_record_projection(staged_record_id)
    if staged is None:
        return None
    parent = find_import(str(staged.get("operational_import_id") or ""))
    envelope = parent.get("envelope") if isinstance(parent, dict) else {}
    envelope = envelope if isinstance(envelope, dict) else {}
    return {
        "entry_type": "promoted_observation",
        "case_id": promotion.get("case_id") or envelope.get("case_id"),
        "entry_id": promotion.get("promotion_id"),
        "event_time": staged.get("observed_at"),
        "report_time": envelope.get("exported_at"),
        "capture_time": envelope.get("imported_at"),
        "valid_from": None,
        "valid_to": None,
        "subject_entity_id": None,
        "object_entity_id": None,
        "relationship_type": None,
        "inference_class": "direct_import_observation",
        "inference_warning": None,
        "limitations": [
            "Promoted observation remains evidence-derived and is not a truth assignment."
        ],
        "relocation_context_only": promotion.get("relocation_context_only") is True,
        "issue_claim_support_allowed": promotion.get("issue_claim_support_allowed") is True,
        "binding_sha256": promotion.get("binding_sha256"),
    }


def _relationship_entry(assessment: dict[str, Any]) -> dict[str, Any]:
    times = assessment.get("times") or {}
    times = times if isinstance(times, dict) else {}
    return {
        "entry_type": "relationship_assessment",
        "case_id": assessment.get("case_id"),
        "entry_id": assessment.get("relationship_timeline_assessment_id"),
        "event_time": times.get("event_time"),
        "report_time": times.get("report_time"),
        "capture_time": times.get("capture_time"),
        "valid_from": times.get("valid_from"),
        "valid_to": times.get("valid_to"),
        "subject_entity_id": assessment.get("subject_entity_id"),
        "object_entity_id": assessment.get("object_entity_id"),
        "relationship_type": assessment.get("relationship_type"),
        "inference_class": assessment.get("inference_class"),
        "inference_warning": assessment.get("inference_warning"),
        "limitations": assessment.get("limitations") or [],
        "relocation_context_only": False,
        "issue_claim_support_allowed": True,
        "binding_sha256": assessment.get("relationship_timeline_assessment_sha256"),
    }


def build_relationship_chronology(
    *,
    case_id: str | None = None,
    entity_id: str | None = None,
) -> dict[str, Any]:
    case_id = str(case_id or "").strip() or None
    entity_id = str(entity_id or "").strip() or None
    entries = [
        item
        for promotion in current_promotions()
        if (item := _promotion_entry(promotion)) is not None
    ]
    entries.extend(
        _relationship_entry(item) for item in current_relationship_assessments()
    )
    if case_id:
        entries = [item for item in entries if item.get("case_id") == case_id]
    if entity_id:
        entries = [
            item
            for item in entries
            if entity_id
            in {item.get("subject_entity_id"), item.get("object_entity_id")}
        ]
    entries = sorted(
        entries,
        key=lambda item: (
            str(item.get("event_time") or ""),
            str(item.get("entry_type") or ""),
            str(item.get("entry_id") or ""),
        ),
    )
    co_occurrences = [
        item for item in entries if item.get("inference_class") == "co_occurrence_only"
    ]
    inferred = [
        item for item in entries if item.get("inference_class") == "supported_inference"
    ]
    relocation = [item for item in entries if item.get("relocation_context_only") is True]
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "ready",
        "read_only": True,
        "case_id": case_id,
        "entity_id": entity_id,
        "entries": entries,
        "summary": {
            "entry_count": len(entries),
            "promoted_observation_count": sum(
                item.get("entry_type") == "promoted_observation" for item in entries
            ),
            "relationship_assessment_count": sum(
                item.get("entry_type") == "relationship_assessment" for item in entries
            ),
            "supported_inference_count": len(inferred),
            "co_occurrence_only_count": len(co_occurrences),
            "relocation_context_count": len(relocation),
        },
        "controls": {
            "event_report_capture_and_validity_times_separate": True,
            "co_occurrence_promoted_to_relationship": False,
            "causation_assigned": False,
            "relationship_asserted_as_truth": False,
            "graph_mutated": False,
            "claim_mutated": False,
            "dossier_mutated": False,
            "write_actions_exposed": [],
        },
    }
