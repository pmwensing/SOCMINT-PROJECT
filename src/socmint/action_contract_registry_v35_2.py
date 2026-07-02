from __future__ import annotations

from copy import deepcopy
from types import MappingProxyType
from typing import Any

from .dossier_assembly_workspace_v21_0 import _sha

SCHEMA = "socmint.action_contract_registry.v35_2"
VERSION = "v35.2.0"
SYSTEM_FIELDS = frozenset(
    {"actor", "reviewer", "operator", "recorder", "case_id", "confirmed", "ip_address"}
)


def _field(kind: str, required: bool = False, values: tuple[str, ...] = ()) -> dict[str, Any]:
    return {"kind": kind, "required": required, "values": values}


_REGISTRY = {
    "create_audience_contract": {
        "service": "audience_recipient_contract_v32_1.record_audience_recipient_contract",
        "actor_field": "actor",
        "fields": {
            "audience_name": _field("string", True),
            "audience_type": _field("string", True, ("internal", "external_partner", "regulatory", "legal", "executive", "public")),
            "dissemination_purpose": _field("string", True),
            "classification": _field("string", True, ("public", "internal", "restricted")),
            "recipients": _field("mapping_list", True),
            "reason": _field("string", True),
            "note": _field("string"),
        },
        "conditions": (),
    },
    "assemble_dissemination_package": {
        "service": "dissemination_package_v32_2.assemble_dissemination_package",
        "actor_field": "actor",
        "fields": {
            "published_revision_id": _field("string", True),
            "audience_contract_id": _field("string", True),
            "package_label": _field("string", True),
            "reason": _field("string", True),
            "note": _field("string"),
        },
        "conditions": (),
    },
    "record_authorization_policy_decision": {
        "service": "authorization_policy_release_gate_v32_3.record_authorization_policy_decision",
        "actor_field": "reviewer",
        "fields": {
            "dissemination_package_id": _field("string", True),
            "decision": _field("string", True, ("approve", "deny", "hold")),
            "reason": _field("string", True),
            "policy_note": _field("string"),
        },
        "conditions": (),
    },
    "record_delivery_attempt": {
        "service": "delivery_attempt_receipt_ledger_v32_4.record_delivery_attempt",
        "actor_field": "operator",
        "fields": {
            "dissemination_package_id": _field("string", True),
            "recipient_id": _field("string", True),
            "delivery_channel": _field("string", True),
            "endpoint_reference": _field("string", True),
            "attempt_result": _field("string", True, ("accepted", "failed", "blocked")),
            "transport_reference": _field("string", True),
            "reason": _field("string", True),
            "failure_code": _field("string"),
            "failure_detail": _field("string"),
            "note": _field("string"),
        },
        "conditions": (("attempt_result", "failed", "failure_code"),),
    },
    "record_delivery_receipt": {
        "service": "delivery_attempt_receipt_ledger_v32_4.record_delivery_receipt",
        "actor_field": "recorder",
        "fields": {
            "delivery_attempt_id": _field("string", True),
            "delivery_result": _field("string", True, ("delivered", "failed", "pending")),
            "provider_message_id": _field("string", True),
            "transport_status": _field("string", True),
            "delivered_at": _field("string"),
            "failure_code": _field("string"),
            "failure_detail": _field("string"),
            "note": _field("string"),
        },
        "conditions": (
            ("delivery_result", "delivered", "delivered_at"),
            ("delivery_result", "failed", "failure_code"),
        ),
    },
    "record_correction_intake": {
        "service": "recipient_feedback_correction_intake_v32_5.record_correction_intake",
        "actor_field": "reviewer",
        "fields": {
            "recipient_feedback_id": _field("string", True),
            "correction_action": _field("string", True, ("no_change", "editorial_review", "new_revision_review", "recall_review")),
            "reason": _field("string", True),
            "affected_section_ids": _field("string_list"),
            "proposed_resolution": _field("string"),
            "note": _field("string"),
        },
        "conditions": (),
    },
    "record_recall_decision": {
        "service": "recall_retention_lifecycle_v32_6.record_recall_decision",
        "actor_field": "reviewer",
        "fields": {
            "correction_intake_id": _field("string", True),
            "decision": _field("string", True, ("initiate", "confirm", "deny", "lift")),
            "reason": _field("string", True),
            "effective_at": _field("string"),
            "replacement_published_revision_id": _field("string"),
            "note": _field("string"),
        },
        "conditions": (),
    },
    "record_retention_decision": {
        "service": "recall_retention_lifecycle_v32_6.record_retention_decision",
        "actor_field": "reviewer",
        "fields": {
            "disposition": _field("string", True, ("retain", "legal_hold", "archive", "expiry_review")),
            "policy_id": _field("string", True),
            "reason": _field("string", True),
            "review_at": _field("string"),
            "note": _field("string"),
        },
        "conditions": (("disposition", "expiry_review", "review_at"),),
    },
}

ACTION_CONTRACT_REGISTRY = MappingProxyType(_REGISTRY)


def contract_for_action(action: str) -> dict[str, Any] | None:
    value = ACTION_CONTRACT_REGISTRY.get(str(action or ""))
    return deepcopy(value) if value is not None else None


def registry_manifest() -> dict[str, Any]:
    actions = {key: deepcopy(ACTION_CONTRACT_REGISTRY[key]) for key in sorted(ACTION_CONTRACT_REGISTRY)}
    content = {
        "schema": SCHEMA,
        "version": VERSION,
        "action_count": len(actions),
        "actions": actions,
        "system_fields": sorted(SYSTEM_FIELDS),
        "reject_unknown_fields": True,
    }
    return {**content, "registry_sha256": _sha(content)}
