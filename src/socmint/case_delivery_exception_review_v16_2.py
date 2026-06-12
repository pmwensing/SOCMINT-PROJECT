from __future__ import annotations

from copy import deepcopy
from typing import Any

from .case_delivery_attempt_ledger_v16_1 import build_case_delivery_attempt_ledger_from_request
from .case_delivery_handoff_package_v15_1 import canonical_json
from .case_delivery_handoff_package_v15_1 import sha256_text


CASE_DELIVERY_EXCEPTION_REVIEW_SCHEMA = "socmint.case_delivery_exception_review.v16_2"
VERSION = "v16.2.0"
EXCEPTION_STATUSES = {"failed", "exception", "timeout"}


def _blocker(key: str, detail: str) -> dict[str, Any]:
    return {"key": key, "detail": detail}


def _exception_category(attempt: dict[str, Any]) -> str:
    detail = str(attempt.get("detail") or "").lower()
    status = attempt.get("status")
    channel = str(attempt.get("channel") or "").lower()
    if status == "timeout" or "timeout" in detail or "timed out" in detail:
        return "timeout"
    if "recipient" in detail and any(term in detail for term in ("unavailable", "missing", "did not acknowledge")):
        return "recipient_unavailable"
    if "reject" in detail or "declined" in detail:
        return "delivery_rejected"
    if "channel" in detail or "outage" in detail or channel == "unspecified":
        return "channel_unavailable"
    return "unclassified_exception"


def _recommended_action(category: str, retryable: bool) -> str:
    if category == "recipient_unavailable":
        return "confirm_recipient_and_retry" if retryable else "confirm_recipient_before_retry"
    if category == "channel_unavailable":
        return "switch_delivery_channel" if retryable else "escalate_channel_failure"
    if category == "timeout":
        return "retry_with_timeout_window" if retryable else "review_timeout_policy"
    if category == "delivery_rejected":
        return "escalate_delivery_rejection"
    return "operator_review_required"


def _exception_rows(attempts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for attempt in attempts:
        if attempt.get("status") not in EXCEPTION_STATUSES:
            continue
        category = _exception_category(attempt)
        payload = {
            "attempt_id": attempt.get("attempt_id"),
            "sequence": attempt.get("sequence"),
            "category": category,
            "status": attempt.get("status"),
            "channel": attempt.get("channel"),
            "operator": attempt.get("operator"),
            "retryable": attempt.get("retryable") is True,
            "recommended_action": _recommended_action(category, attempt.get("retryable") is True),
        }
        rows.append(
            {
                **payload,
                "exception_id": sha256_text(canonical_json(payload)),
            }
        )
    return rows


def _review_state(ledger: dict[str, Any], exceptions: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    blockers = []
    if ledger.get("state") == "blocked":
        blockers.extend(deepcopy(ledger.get("blockers") or []))
        blockers.append(_blocker("attempt_ledger_blocked", "delivery attempt ledger is blocked"))
        return "blocked", blockers
    if not exceptions:
        return "clear", blockers
    if any(exception.get("category") in {"delivery_rejected", "unclassified_exception"} for exception in exceptions):
        return "escalation_required", blockers
    return "review_required", blockers


def build_case_delivery_exception_review(
    case_id: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    safe_payload = deepcopy(payload or {})
    ledger = (
        deepcopy(safe_payload.get("attempt_ledger"))
        if isinstance(safe_payload.get("attempt_ledger"), dict)
        else build_case_delivery_attempt_ledger_from_request(case_id, safe_payload)
    )
    attempts = ledger.get("attempts") if isinstance(ledger.get("attempts"), list) else []
    exceptions = _exception_rows([attempt for attempt in attempts if isinstance(attempt, dict)])
    state, blockers = _review_state(ledger, exceptions)
    payload_core = {
        "schema": CASE_DELIVERY_EXCEPTION_REVIEW_SCHEMA,
        "version": VERSION,
        "case_id": case_id,
        "ledger_id": ledger.get("ledger_id"),
        "state": state,
        "exception_count": len(exceptions),
        "retryable_exception_count": sum(1 for exception in exceptions if exception.get("retryable") is True),
        "blocker_count": len(blockers),
    }
    result = {
        **payload_core,
        "attempt_ledger": ledger,
        "exceptions": exceptions,
        "blockers": blockers,
        "next_action": "continue_delivery" if state == "clear" else "review_delivery_exceptions",
    }
    return {
        **result,
        "review_id": sha256_text(canonical_json(result)),
    }


def build_case_delivery_exception_review_from_request(case_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    return build_case_delivery_exception_review(case_id, payload)
