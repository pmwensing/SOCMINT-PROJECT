from __future__ import annotations

from typing import Any

from .action_queue_blocker_surface_v33_2 import build_case_action_queue
from .case_governance_snapshot_v33_1 import build_case_governance_snapshot
from .dossier_assembly_workspace_v21_0 import _sha
from .recall_retention_lifecycle_v32_6 import (
    current_recall_state,
    current_retention_state,
    lifecycle_snapshot,
    recall_decision_history,
    retention_decision_history,
)

SCHEMA = "socmint.recall_retention_lifecycle_timeline.v33_5"
VERSION = "v33.5.0"
SENSITIVE = ("endpoint", "contact_secret", "credential", "password", "token")


def _for_case(rows: list[dict[str, Any]], case_id: str) -> list[dict[str, Any]]:
    return [row for row in rows if str(row.get("case_id") or "") == case_id]


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _sanitize(item)
            for key, item in value.items()
            if not any(
                part in str(key).lower().replace("-", "_").replace(" ", "_")
                for part in SENSITIVE
            )
        }
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    return value


def _timeline_event(stage: str, item: dict[str, Any]) -> dict[str, Any]:
    content = {
        "stage": stage,
        "recorded_at": item.get("recorded_at"),
        "record_id": item.get("recall_decision_id")
        or item.get("retention_decision_id"),
        "state": item.get("recall_state") or item.get("retention_state"),
        "record": _sanitize(item),
    }
    return {**content, "event_sha256": _sha(content)}


def build_case_recall_retention_lifecycle_timeline(case_id: str) -> dict[str, Any]:
    case_id = str(case_id or "").strip()
    snapshot = build_case_governance_snapshot(case_id)
    if snapshot.get("status") == "blocked":
        return {"schema": SCHEMA, "version": VERSION, "status": "blocked", "case_id": snapshot.get("case_id") or "", "blockers": snapshot.get("blockers") or [], "read_only": True, "source_records_mutated": False}

    queue = build_case_action_queue(case_id)
    recalls = _for_case(recall_decision_history(), case_id)
    retentions = _for_case(retention_decision_history(), case_id)
    package_ids = sorted({str(item.get("dissemination_package_id") or "") for item in recalls if item.get("dissemination_package_id")})
    recall_states = {package_id: current_recall_state(package_id) for package_id in package_ids}
    timeline = [_timeline_event("recall", item) for item in recalls] + [_timeline_event("retention", item) for item in retentions]
    timeline.sort(key=lambda item: (str(item.get("recorded_at") or ""), str(item.get("record_id") or "")))
    blockers = [_sanitize(item) for item in snapshot.get("blockers") or [] if item.get("stage") in {"recall", "retention"}]
    actions = [_sanitize(item) for item in queue.get("action_queue") or [] if item.get("stage") in {"recall", "retention"}]
    content = {
        "case_id": case_id,
        "snapshot_sha256": snapshot.get("snapshot_sha256"),
        "queue_summary_sha256": queue.get("queue_summary_sha256"),
        "current_recall_states": recall_states,
        "current_retention_state": current_retention_state(case_id),
        "recall_history": _sanitize(recalls),
        "retention_history": _sanitize(retentions),
        "timeline": timeline,
        "lifecycle_snapshot": _sanitize(lifecycle_snapshot(case_id)),
        "blockers": blockers,
        "available_actions": actions,
    }
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "attention_required" if blockers else "ready",
        **content,
        "timeline_sha256": _sha(content),
        "read_only": True,
        "actions_executed": False,
        "actions_delegate_to_v32_services": True,
        "human_confirmation_required": True,
        "historical_evidence_preserved": True,
        "source_records_mutated": False,
        "next_action": queue.get("next_action") or "review_lifecycle_timeline",
    }
