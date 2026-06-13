from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any

from .case_delivery_handoff_package_v15_1 import canonical_json
from .case_delivery_handoff_package_v15_1 import sha256_text
from .operator_workflow_action_receipt_v17_3 import OPERATOR_WORKFLOW_ACTION_RECEIPT_SCHEMA


OPERATOR_WORKFLOW_ACTION_RECEIPT_VERIFICATION_SCHEMA = "socmint.operator_workflow_action_receipt_verification.v17_4"
VERSION = "v17.4.0"

RECEIPT_PAYLOAD_FIELDS = (
    "schema",
    "version",
    "case_id",
    "operator",
    "action",
    "label",
    "confirmed",
    "requires_confirmation",
    "state_change",
    "action_target",
    "action_plan_type",
    "result_status",
    "result_next_action",
    "blocker_count",
    "recorded_at",
)


def _blocker(key: str, detail: str) -> dict[str, str]:
    return {"key": key, "detail": detail}


def _receipt_payload(receipt: dict[str, Any]) -> dict[str, Any]:
    return {field: receipt.get(field) for field in RECEIPT_PAYLOAD_FIELDS}


def _action_target(action_result: dict[str, Any]) -> str | None:
    plan = action_result.get("action_plan")
    if not isinstance(plan, dict):
        return None
    target = plan.get("target") or plan.get("command")
    return str(target) if target is not None else None


def _timestamp_present_and_valid(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def verify_operator_workflow_action_receipt(
    receipt: dict[str, Any] | None,
    action_result: dict[str, Any] | None = None,
    *,
    expected_operator: str | None = None,
    expected_case_id: str | None = None,
) -> dict[str, Any]:
    safe_receipt = deepcopy(receipt or {})
    safe_result = deepcopy(action_result or {})
    blockers: list[dict[str, str]] = []

    if not safe_receipt:
        blockers.append(_blocker("missing_action_receipt", "operator action receipt is missing"))

    if safe_receipt and safe_receipt.get("schema") != OPERATOR_WORKFLOW_ACTION_RECEIPT_SCHEMA:
        blockers.append(_blocker("receipt_schema_mismatch", "receipt schema does not match v17.3"))

    expected_hash = sha256_text(canonical_json(_receipt_payload(safe_receipt))) if safe_receipt else None
    if safe_receipt and safe_receipt.get("receipt_sha256") != expected_hash:
        blockers.append(_blocker("receipt_hash_mismatch", "receipt_sha256 does not match canonical receipt payload"))

    expected_receipt_id = (
        sha256_text(
            canonical_json(
                {
                    **_receipt_payload(safe_receipt),
                    "receipt_sha256": safe_receipt.get("receipt_sha256"),
                }
            )
        )
        if safe_receipt
        else None
    )
    if safe_receipt and safe_receipt.get("action_receipt_id") != expected_receipt_id:
        blockers.append(_blocker("action_receipt_id_mismatch", "action_receipt_id does not match canonical receipt payload"))

    if safe_receipt and not _timestamp_present_and_valid(safe_receipt.get("recorded_at")):
        blockers.append(_blocker("invalid_recorded_at", "recorded_at timestamp is missing or invalid"))

    if safe_receipt and not isinstance(safe_receipt.get("operator"), str):
        blockers.append(_blocker("operator_missing", "receipt operator is missing"))
    elif safe_receipt and not str(safe_receipt.get("operator") or "").strip():
        blockers.append(_blocker("operator_missing", "receipt operator is empty"))

    if expected_operator is not None and safe_receipt.get("operator") != expected_operator:
        blockers.append(_blocker("operator_mismatch", "receipt operator does not match authenticated operator"))
    if expected_case_id is not None and safe_receipt.get("case_id") != expected_case_id:
        blockers.append(_blocker("case_id_mismatch", "receipt case_id does not match requested case"))

    if safe_result:
        comparisons = (
            ("action", safe_result.get("action"), "action_mismatch"),
            ("label", safe_result.get("label"), "label_mismatch"),
            ("confirmed", safe_result.get("confirmed") is True, "confirmation_state_mismatch"),
            (
                "requires_confirmation",
                safe_result.get("requires_confirmation") is True,
                "confirmation_requirement_mismatch",
            ),
            ("state_change", safe_result.get("state_change") is True, "state_change_mismatch"),
            ("result_status", safe_result.get("status"), "result_status_mismatch"),
            ("result_next_action", safe_result.get("next_action"), "result_next_action_mismatch"),
            ("blocker_count", int(safe_result.get("blocker_count") or 0), "blocker_count_mismatch"),
        )
        for field, expected, key in comparisons:
            if safe_receipt.get(field) != expected:
                blockers.append(_blocker(key, f"receipt {field} does not match action result"))

        expected_target = _action_target(safe_result)
        if safe_receipt.get("action_target") != expected_target:
            blockers.append(_blocker("action_target_mismatch", "receipt action target does not match action plan"))
        expected_plan_type = (
            safe_result.get("action_plan", {}).get("type")
            if isinstance(safe_result.get("action_plan"), dict)
            else None
        )
        if safe_receipt.get("action_plan_type") != expected_plan_type:
            blockers.append(_blocker("action_plan_type_mismatch", "receipt action plan type does not match action result"))

    status = "verified" if not blockers else "blocked"
    return {
        "schema": OPERATOR_WORKFLOW_ACTION_RECEIPT_VERIFICATION_SCHEMA,
        "version": VERSION,
        "case_id": safe_receipt.get("case_id") or expected_case_id,
        "action_receipt_id": safe_receipt.get("action_receipt_id"),
        "status": status,
        "verified": not blockers,
        "receipt_hash_valid": safe_receipt.get("receipt_sha256") == expected_hash if safe_receipt else False,
        "receipt_id_valid": safe_receipt.get("action_receipt_id") == expected_receipt_id if safe_receipt else False,
        "timestamp_valid": _timestamp_present_and_valid(safe_receipt.get("recorded_at")) if safe_receipt else False,
        "operator_consistent": not any(item["key"] in {"operator_missing", "operator_mismatch"} for item in blockers),
        "action_result_consistent": not any(
            item["key"]
            in {
                "action_mismatch",
                "label_mismatch",
                "confirmation_state_mismatch",
                "confirmation_requirement_mismatch",
                "state_change_mismatch",
                "result_status_mismatch",
                "result_next_action_mismatch",
                "blocker_count_mismatch",
            }
            for item in blockers
        ),
        "action_target_valid": not any(
            item["key"] in {"action_target_mismatch", "action_plan_type_mismatch"}
            for item in blockers
        ),
        "blocker_count": len(blockers),
        "blockers": blockers,
        "next_action": "accept_operator_action_receipt" if not blockers else "resolve_operator_action_receipt",
    }


def verify_operator_workflow_action_receipt_from_request(
    case_id: str,
    payload: dict[str, Any] | None,
    *,
    expected_operator: str | None = None,
) -> dict[str, Any]:
    safe_payload = deepcopy(payload or {})
    receipt = safe_payload.get("action_receipt") if isinstance(safe_payload.get("action_receipt"), dict) else None
    action_result = safe_payload.get("action_result") if isinstance(safe_payload.get("action_result"), dict) else None
    return verify_operator_workflow_action_receipt(
        receipt,
        action_result,
        expected_operator=expected_operator,
        expected_case_id=case_id,
    )
