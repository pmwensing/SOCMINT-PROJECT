from __future__ import annotations

from typing import Any

from .action_queue_blocker_surface_v33_2 import build_case_action_queue
from .audience_package_authorization_panels_v33_3 import (
    build_case_audience_package_authorization_panels,
)
from .case_governance_snapshot_v33_1 import build_case_governance_snapshot
from .delivery_receipt_feedback_panels_v33_4 import (
    build_case_delivery_receipt_feedback_panels,
)
from .dossier_assembly_workspace_v21_0 import _sha
from .recall_retention_lifecycle_timeline_v33_5 import (
    build_case_recall_retention_lifecycle_timeline,
)

SCHEMA = "socmint.case_centric_operator_workspace.v33_6"
VERSION = "v33.6.0"


def build_case_centric_operator_workspace(case_id: str) -> dict[str, Any]:
    case_id = str(case_id or "").strip()
    snapshot = build_case_governance_snapshot(case_id)
    if snapshot.get("status") == "blocked":
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "status": "blocked",
            "case_id": snapshot.get("case_id") or "",
            "blockers": snapshot.get("blockers") or [],
            "read_only": True,
            "actions_executed": False,
        }

    queue = build_case_action_queue(case_id)
    governance = build_case_audience_package_authorization_panels(case_id)
    delivery = build_case_delivery_receipt_feedback_panels(case_id)
    lifecycle = build_case_recall_retention_lifecycle_timeline(case_id)
    sections = {
        "overview": snapshot,
        "action_queue": queue,
        "audience_package_authorization": governance,
        "delivery_receipt_feedback": delivery,
        "recall_retention_lifecycle": lifecycle,
    }
    blockers = snapshot.get("blockers") or []
    content = {
        "case_id": case_id,
        "section_order": [
            "overview",
            "action_queue",
            "audience_package_authorization",
            "delivery_receipt_feedback",
            "recall_retention_lifecycle",
        ],
        "sections": sections,
        "summary": {
            "blocker_count": len(blockers),
            "action_count": len(queue.get("action_queue") or []),
            "current_stage": (queue.get("action_queue") or [{}])[0].get("stage"),
            "next_action": queue.get("next_action") or snapshot.get("next_action"),
            "retention_state": lifecycle.get("current_retention_state"),
            "recalled_package_count": sum(
                state in {"recall_pending", "recalled"}
                for state in (lifecycle.get("current_recall_states") or {}).values()
            ),
        },
    }
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "attention_required" if blockers else "ready",
        **content,
        "workspace_sha256": _sha(content),
        "read_only": True,
        "canonical_browser_api_read_model": True,
        "actions_executed": False,
        "actions_delegate_to_v32_services": True,
        "human_confirmation_required": True,
        "source_records_mutated": False,
        "next_action": content["summary"]["next_action"] or "review_case_governance",
    }
