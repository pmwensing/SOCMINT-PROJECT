from __future__ import annotations

from .dossier_export_readiness_v37_7 import current_export_readiness_records
from .guided_analyst_workflow_v37_5 import build_guided_analyst_workflow
from .relationship_chronology_workflow_v37_6 import build_relationship_chronology


def build_operational_case_intelligence_workspace():
    workflow = build_guided_analyst_workflow()
    chronology = build_relationship_chronology()
    readiness = current_export_readiness_records()
    ready_count = sum(item.get("readiness_status") == "ready" for item in readiness)
    return {
        "schema": "socmint.operational_case_intelligence_workspace.v37_8",
        "version": "v37.8.0",
        "status": "ready",
        "read_only": True,
        "summary": {
            **(workflow.get("summary") or {}),
            "chronology_entry_count": int(
                (chronology.get("summary") or {}).get("entry_count") or 0
            ),
            "export_readiness_record_count": len(readiness),
            "export_ready_count": ready_count,
        },
        "findings": workflow.get("findings") or [],
        "workflow": workflow,
        "chronology": chronology,
        "export_readiness_inventory": readiness,
        "controls": {
            "automatic_collection": False,
            "automatic_observation_promotion": False,
            "automatic_entity_merge": False,
            "automatic_claim_approval": False,
            "automatic_dossier_mutation": False,
            "automatic_export": False,
            "automatic_publication": False,
            "write_actions_exposed_by_workspace": [],
        },
    }
