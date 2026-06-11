from __future__ import annotations

from copy import deepcopy
from typing import Any

from .case_delivery_execution_envelope_v15_6 import build_case_delivery_execution_envelope_from_request
from .case_delivery_handoff_package_v15_1 import canonical_json
from .case_delivery_handoff_package_v15_1 import sha256_text


CASE_DELIVERY_OPERATIONS_SCHEMA = "socmint.case_delivery_operations.v16_0"
VERSION = "v16.0.0"


def _blocker(key: str, detail: str) -> dict[str, Any]:
    return {"key": key, "detail": detail}


def _event_rows(events: list[Any]) -> list[dict[str, Any]]:
    rows = []
    for index, event in enumerate(events, start=1):
        if not isinstance(event, dict):
            continue
        event_type = event.get("type") or event.get("event_type") or "operator_note"
        status = event.get("status") or ("blocked" if event_type in {"blocked", "exception"} else "recorded")
        payload = {
            "sequence": index,
            "type": event_type,
            "status": status,
            "operator": event.get("operator") or "unassigned",
            "detail": event.get("detail") or "",
        }
        rows.append(
            {
                **payload,
                "event_id": sha256_text(canonical_json(payload)),
            }
        )
    return rows


def _operation_state(envelope_result: dict[str, Any], events: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    blockers = []
    if envelope_result.get("executable") is not True:
        blockers.extend(deepcopy(envelope_result.get("blockers") or []))
        blockers.append(_blocker("execution_envelope_blocked", "delivery execution envelope is not ready"))
    if any(event.get("type") in {"blocked", "exception"} for event in events):
        blockers.append(_blocker("operator_exception", "operator event log contains a blocking delivery event"))
    if blockers:
        return "blocked", blockers
    if any(event.get("type") == "dispatch_confirmed" for event in events):
        return "dispatched", blockers
    return "ready_for_dispatch", blockers


def build_case_delivery_operations(
    case_id: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    safe_payload = deepcopy(payload or {})
    envelope_result = (
        deepcopy(safe_payload.get("execution_envelope_result"))
        if isinstance(safe_payload.get("execution_envelope_result"), dict)
        else build_case_delivery_execution_envelope_from_request(case_id, safe_payload)
    )
    envelope = envelope_result.get("envelope") if isinstance(envelope_result.get("envelope"), dict) else {}
    events = _event_rows(safe_payload.get("events") if isinstance(safe_payload.get("events"), list) else [])
    state, blockers = _operation_state(envelope_result, events)
    payload_core = {
        "schema": CASE_DELIVERY_OPERATIONS_SCHEMA,
        "version": VERSION,
        "case_id": case_id,
        "delivery_id": envelope.get("delivery_id"),
        "execution_id": envelope.get("execution_id"),
        "authorization_id": envelope.get("authorization_id") or envelope_result.get("authorization_id"),
        "state": state,
        "dispatchable": state in {"ready_for_dispatch", "dispatched"},
        "event_count": len(events),
        "blocker_count": len(blockers),
    }
    result = {
        **payload_core,
        "execution_envelope": envelope,
        "events": events,
        "blockers": blockers,
        "next_action": "dispatch_delivery" if state == "ready_for_dispatch" else "review_delivery_operations",
    }
    return {
        **result,
        "operation_id": sha256_text(canonical_json(result)),
    }


def build_case_delivery_operations_from_request(case_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    return build_case_delivery_operations(case_id, payload)
