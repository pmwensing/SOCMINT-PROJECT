from __future__ import annotations

from copy import deepcopy
from typing import Any


OPERATOR_ACTION_SESSION_TIMELINE_SCHEMA = (
    "socmint.operator_action_session_timeline.v17_5"
)
VERSION = "v17.5.0"
SESSION_KEY = "operator_action_history_v17_5"
DEFAULT_MAX_ENTRIES = 20


def _timeline_entry(
    action_receipt: dict[str, Any],
    verification: dict[str, Any] | None = None,
) -> dict[str, Any]:
    safe_receipt = deepcopy(action_receipt or {})
    safe_verification = deepcopy(verification or {})
    return {
        "action_receipt_id": safe_receipt.get("action_receipt_id"),
        "case_id": safe_receipt.get("case_id"),
        "operator": safe_receipt.get("operator"),
        "action": safe_receipt.get("action"),
        "label": safe_receipt.get("label"),
        "confirmed": safe_receipt.get("confirmed") is True,
        "state_change": safe_receipt.get("state_change") is True,
        "action_target": safe_receipt.get("action_target"),
        "result_status": safe_receipt.get("result_status"),
        "recorded_at": safe_receipt.get("recorded_at"),
        "verification_status": safe_verification.get("status"),
        "verified": safe_verification.get("verified") is True,
        "verification_blocker_count": int(safe_verification.get("blocker_count") or 0),
        "verification_next_action": safe_verification.get("next_action"),
    }


def append_operator_action_history(
    history: list[dict[str, Any]] | None,
    action_receipt: dict[str, Any],
    verification: dict[str, Any] | None = None,
    *,
    max_entries: int = DEFAULT_MAX_ENTRIES,
) -> list[dict[str, Any]]:
    safe_history = [
        deepcopy(item) for item in (history or []) if isinstance(item, dict)
    ]
    entry = _timeline_entry(action_receipt, verification)
    if not entry.get("action_receipt_id"):
        return safe_history[-max_entries:]
    safe_history = [
        item
        for item in safe_history
        if item.get("action_receipt_id") != entry.get("action_receipt_id")
    ]
    safe_history.append(entry)
    return safe_history[-max(1, int(max_entries)) :]


def build_operator_action_session_timeline(
    history: list[dict[str, Any]] | None,
    *,
    case_id: str | None = None,
    operator: str | None = None,
) -> dict[str, Any]:
    entries = [deepcopy(item) for item in (history or []) if isinstance(item, dict)]
    if operator is not None:
        entries = [item for item in entries if item.get("operator") == operator]
    if case_id is not None:
        entries = [item for item in entries if item.get("case_id") == case_id]
    entries.sort(key=lambda item: str(item.get("recorded_at") or ""), reverse=True)
    verified_count = sum(1 for item in entries if item.get("verified") is True)
    blocked_count = sum(
        1
        for item in entries
        if item.get("verification_status") == "blocked"
        or item.get("result_status") == "blocked"
    )
    confirmation_required_count = sum(
        1 for item in entries if item.get("result_status") == "confirmation_required"
    )
    return {
        "schema": OPERATOR_ACTION_SESSION_TIMELINE_SCHEMA,
        "version": VERSION,
        "case_id": case_id,
        "operator": operator,
        "entry_count": len(entries),
        "verified_count": verified_count,
        "blocked_count": blocked_count,
        "confirmation_required_count": confirmation_required_count,
        "entries": entries,
        "persistence": "flask_session_only",
        "next_action": "review_operator_action_history"
        if entries
        else "launch_operator_action",
    }
