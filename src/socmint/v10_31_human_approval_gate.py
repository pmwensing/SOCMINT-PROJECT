from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from .v10_30_case_delivery_registry import build_case_delivery_registry_from_request
from .v10_30_case_delivery_registry import get_delivery_by_id

HUMAN_APPROVAL_GATE_SCHEMA = "socmint.v10_31.human_approval_gate"
HUMAN_APPROVAL_SUMMARY_SCHEMA = "socmint.v10_31.human_approval_gate.summary"
VERSION = "v10.31.0"
VALID_DECISIONS = {"approved", "rejected", "needs_correction", "pending_review"}

DECISION_ACTIONS = {
    "approved": {
        "allowed": ["export_zip", "record_delivery", "archive_case_delivery"],
        "blocked": ["reject_delivery", "request_correction"],
    },
    "rejected": {
        "allowed": ["revise_delivery", "regenerate_export"],
        "blocked": ["record_delivery", "archive_case_delivery"],
    },
    "needs_correction": {
        "allowed": ["revise_delivery", "rerun_registry", "request_review"],
        "blocked": ["record_delivery", "archive_case_delivery"],
    },
    "pending_review": {
        "allowed": [
            "review_delivery",
            "approve_delivery",
            "reject_delivery",
            "request_correction",
        ],
        "blocked": ["record_delivery", "archive_case_delivery"],
    },
}


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def canonical_json(data: dict[str, Any]) -> str:
    return (
        json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    )


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_decision(decision: str | None) -> str:
    value = (decision or "pending_review").strip().lower()
    return value if value in VALID_DECISIONS else "pending_review"


def approval_id_for_decision(
    *,
    case_id: str,
    delivery_id: str | None,
    decision: str,
    operator: str | None = None,
    notes: str | None = None,
) -> str:
    core = {
        "case_id": case_id,
        "delivery_id": delivery_id,
        "decision": normalize_decision(decision),
        "operator": operator or "",
        "notes": notes or "",
    }
    return sha256_text(canonical_json(core))


def actions_for_decision(decision: str | None) -> dict[str, list[str]]:
    normalized = normalize_decision(decision)
    mapping = DECISION_ACTIONS[normalized]
    return {"allowed": list(mapping["allowed"]), "blocked": list(mapping["blocked"])}


def summarize_approval_gate(gate: dict[str, Any]) -> dict[str, Any]:
    delivery = gate.get("delivery") if isinstance(gate.get("delivery"), dict) else {}
    return {
        "schema": HUMAN_APPROVAL_SUMMARY_SCHEMA,
        "version": VERSION,
        "case_id": gate.get("case_id"),
        "delivery_id": gate.get("delivery_id"),
        "approval_id": gate.get("approval_id"),
        "decision": gate.get("decision"),
        "operator": gate.get("operator"),
        "notes": gate.get("notes"),
        "readiness": delivery.get("readiness"),
        "allowed_actions": list(gate.get("allowed_actions") or []),
        "blocked_actions": list(gate.get("blocked_actions") or []),
        "found": bool(gate.get("found", True)),
    }


def build_human_approval_gate(
    *,
    case_id: str,
    registry: dict[str, Any],
    delivery_id: str | None = None,
    decision: str | None = None,
    operator: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    safe_registry = deepcopy(registry or {})
    selected_delivery_id = delivery_id or safe_registry.get("latest_delivery_id")
    delivery = get_delivery_by_id(safe_registry, selected_delivery_id)
    normalized_decision = normalize_decision(decision)
    approval_id = approval_id_for_decision(
        case_id=case_id,
        delivery_id=selected_delivery_id,
        decision=normalized_decision,
        operator=operator,
        notes=notes,
    )
    actions = actions_for_decision(normalized_decision)
    gate: dict[str, Any] = {
        "schema": HUMAN_APPROVAL_GATE_SCHEMA,
        "version": VERSION,
        "case_id": case_id,
        "delivery_id": selected_delivery_id,
        "approval_id": approval_id,
        "decision": normalized_decision,
        "operator": operator,
        "notes": notes,
        "decided_at": utc_now(),
        "allowed_actions": actions["allowed"],
        "blocked_actions": actions["blocked"],
        "delivery": deepcopy(delivery or {}),
        "registry": safe_registry,
        "found": delivery is not None,
        "summary": {},
    }
    gate["summary"] = summarize_approval_gate(gate)
    return gate


def _registry_from_payload(case_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    safe_payload = deepcopy(payload or {})
    if isinstance(safe_payload.get("registry"), dict):
        return safe_payload["registry"]
    return build_case_delivery_registry_from_request(case_id, safe_payload)


def build_human_approval_gate_from_request(
    case_id: str, payload: dict[str, Any]
) -> dict[str, Any]:
    safe_payload = deepcopy(payload or {})
    registry = _registry_from_payload(case_id, safe_payload)
    return build_human_approval_gate(
        case_id=case_id,
        registry=registry,
        delivery_id=safe_payload.get("delivery_id"),
        decision=safe_payload.get("decision"),
        operator=safe_payload.get("operator"),
        notes=safe_payload.get("notes"),
    )


def build_human_approval_summary_from_request(
    case_id: str, payload: dict[str, Any]
) -> dict[str, Any]:
    return deepcopy(
        build_human_approval_gate_from_request(case_id, payload).get("summary") or {}
    )
