from __future__ import annotations

from copy import deepcopy
from typing import Any

from .case_delivery_exception_review_v16_2 import build_case_delivery_exception_review_from_request
from .case_delivery_handoff_package_v15_1 import canonical_json
from .case_delivery_handoff_package_v15_1 import sha256_text


CASE_DELIVERY_RECOVERY_SCHEMA = "socmint.case_delivery_recovery.v16_3"
VERSION = "v16.3.0"

ESCALATION_CATEGORIES = {"delivery_rejected", "unclassified_exception"}


def _blocker(key: str, detail: str) -> dict[str, Any]:
    return {"key": key, "detail": detail}


def _recovery_action(exception: dict[str, Any]) -> str:
    category = exception.get("category")
    retryable = exception.get("retryable") is True
    if category == "recipient_unavailable":
        return "retry" if retryable else "hold"
    if category == "channel_unavailable":
        return "remediate" if retryable else "escalate"
    if category == "timeout":
        return "retry" if retryable else "hold"
    if category in ESCALATION_CATEGORIES:
        return "escalate"
    return "hold"


def _recommendation(action: str, exception: dict[str, Any]) -> str:
    category = exception.get("category")
    if action == "retry":
        if category == "timeout":
            return "retry_with_extended_timeout_window"
        return "retry_after_operator_confirmation"
    if action == "remediate":
        return "remediate_channel_and_retry"
    if action == "escalate":
        return "escalate_to_delivery_owner"
    return "hold_until_exception_resolved"


def _queue_state(action: str) -> str:
    if action == "retry":
        return "ready_for_retry"
    if action == "remediate":
        return "remediation_required"
    if action == "escalate":
        return "escalation_required"
    return "hold"


def _recovery_rows(exceptions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for sequence, exception in enumerate(exceptions, start=1):
        if not isinstance(exception, dict):
            continue
        action = _recovery_action(exception)
        payload = {
            "exception_id": exception.get("exception_id"),
            "attempt_id": exception.get("attempt_id"),
            "sequence": sequence,
            "category": exception.get("category"),
            "decision": action,
            "queue_state": _queue_state(action),
            "recommendation": _recommendation(action, exception),
        }
        rows.append({**payload, "recovery_id": sha256_text(canonical_json(payload))})
    return rows


def _summary_state(review: dict[str, Any], recoveries: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    blockers = []
    if review.get("state") == "blocked":
        blockers.extend(deepcopy(review.get("blockers") or []))
        blockers.append(_blocker("exception_review_blocked", "delivery exception review is blocked"))
        return "blocked", blockers
    if not recoveries:
        return "clear", blockers
    decisions = {row.get("decision") for row in recoveries}
    if "escalate" in decisions:
        return "escalation_required", blockers
    if "remediate" in decisions:
        return "remediation_required", blockers
    if "retry" in decisions:
        return "retry_ready", blockers
    return "hold", blockers


def _next_action(state: str) -> str:
    if state == "clear":
        return "continue_delivery"
    if state == "retry_ready":
        return "operator_retry_delivery"
    if state == "remediation_required":
        return "remediate_delivery_channel"
    if state == "escalation_required":
        return "escalate_delivery_exception"
    if state == "blocked":
        return "resolve_recovery_blockers"
    return "hold_delivery"


def build_case_delivery_recovery(
    case_id: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    safe_payload = deepcopy(payload or {})
    review = (
        deepcopy(safe_payload.get("exception_review"))
        if isinstance(safe_payload.get("exception_review"), dict)
        else build_case_delivery_exception_review_from_request(case_id, safe_payload)
    )
    exceptions = review.get("exceptions") if isinstance(review.get("exceptions"), list) else []
    recoveries = _recovery_rows([item for item in exceptions if isinstance(item, dict)])
    state, blockers = _summary_state(review, recoveries)
    payload_core = {
        "schema": CASE_DELIVERY_RECOVERY_SCHEMA,
        "version": VERSION,
        "case_id": case_id,
        "review_id": review.get("review_id"),
        "state": state,
        "recovery_count": len(recoveries),
        "retry_count": sum(1 for row in recoveries if row.get("decision") == "retry"),
        "hold_count": sum(1 for row in recoveries if row.get("decision") == "hold"),
        "escalate_count": sum(1 for row in recoveries if row.get("decision") == "escalate"),
        "remediate_count": sum(1 for row in recoveries if row.get("decision") == "remediate"),
        "blocker_count": len(blockers),
    }
    return {
        **payload_core,
        "queue_id": sha256_text(canonical_json(payload_core)),
        "exception_review": review,
        "operator_recovery_queue": recoveries,
        "blockers": blockers,
        "next_action": _next_action(state),
    }


def build_case_delivery_recovery_from_request(case_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    return build_case_delivery_recovery(case_id, payload)
