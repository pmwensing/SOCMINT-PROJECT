from __future__ import annotations

from typing import Any

from . import database
from .dossier_assembly_workspace_v21_0 import (
    _canonical,
    _ensure_storage,
    _json_details,
    _sha,
)

SCHEMA = "socmint.role_permission_access_policy.v28_2"
VERSION = "v28.2.0"
ACTIONS = (
    "administration_role_defined",
    "administration_role_revised",
    "administration_case_access_granted",
    "administration_case_access_denied",
    "administration_case_access_revoked",
)
EFFECTS = ("allow", "deny")
PERMISSIONS = (
    "case.read",
    "case.write",
    "evidence.read",
    "evidence.write",
    "finding.read",
    "finding.write",
    "review.request",
    "review.decide",
    "closure.request",
    "closure.approve",
    "archive.read",
    "archive.manage",
    "cross_case.read",
    "report.generate",
    "administration.read",
)


def blocked(key: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key}],
        "policy_records_mutated": False,
        "case_access_scope_changed": False,
    }


def history() -> list[dict[str, Any]]:
    _ensure_storage()
    session = database.Session()
    try:
        rows = (
            session.query(database.AuditLog)
            .filter(database.AuditLog.action.in_(ACTIONS))
            .order_by(database.AuditLog.created_at.asc(), database.AuditLog.id.asc())
            .all()
        )
        return [
            {
                **_json_details(row),
                "audit_record_id": row.id,
                "actor": row.actor,
                "source_action": row.action,
                "target_value": row.target_value,
                "recorded_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    finally:
        session.close()


def _record(
    action: str, event: dict[str, Any], actor: str, target: str, ip_address: str | None
) -> dict[str, Any]:
    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=actor,
            action=action,
            target_value=target,
            ip_address=ip_address,
            details=_canonical(event),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return {
            **event,
            "audit_record_id": row.id,
            "actor": actor,
            "source_action": action,
            "target_value": target,
            "recorded_at": row.created_at.isoformat() if row.created_at else None,
        }
    finally:
        session.close()


def current_roles() -> list[dict[str, Any]]:
    roles: dict[str, dict[str, Any]] = {}
    for event in history():
        if event.get("event_type") not in {"role_defined", "role_revised"}:
            continue
        role_id = str(event.get("role_id") or "")
        if not role_id:
            continue
        previous = str(event.get("supersedes_role_id") or "")
        if previous in roles:
            roles[previous] = {
                **roles[previous],
                "role_status": "superseded",
                "superseded_by_role_id": role_id,
            }
        roles[role_id] = {**event, "role_status": "active"}
    return sorted(roles.values(), key=lambda item: str(item.get("name") or ""))


def find_role(role_id: str) -> dict[str, Any] | None:
    return next(
        (item for item in current_roles() if item.get("role_id") == role_id), None
    )


def current_access_rules() -> list[dict[str, Any]]:
    rules: dict[str, dict[str, Any]] = {}
    revoked: set[str] = set()
    for event in history():
        event_type = event.get("event_type")
        rule_id = str(event.get("access_rule_id") or "")
        if event_type in {"case_access_granted", "case_access_denied"} and rule_id:
            rules[rule_id] = {**event, "rule_status": "active"}
        elif event_type == "case_access_revoked":
            revoked_id = str(event.get("revoked_access_rule_id") or "")
            if revoked_id:
                revoked.add(revoked_id)
    return [
        {**item, "rule_status": "revoked" if rule_id in revoked else "active"}
        for rule_id, item in sorted(rules.items())
    ]


def define_role(
    *,
    actor: str,
    name: str,
    permissions: Any,
    inherits_role_ids: Any,
    description: str,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    name = str(name or "").strip()
    reason = str(reason or "").strip()
    permission_set = sorted(
        {str(item) for item in (permissions or []) if str(item) in PERMISSIONS}
    )
    inherited = sorted({str(item) for item in (inherits_role_ids or []) if str(item)})
    if confirmed is not True:
        return blocked("explicit_role_definition_confirmation_required")
    if not name:
        return blocked("role_name_required")
    if not reason:
        return blocked("administrative_reason_required")
    if len(permission_set) != len(
        {str(item) for item in (permissions or []) if str(item)}
    ):
        return blocked("permission_invalid")
    active_names = {
        str(item.get("name") or "").lower()
        for item in current_roles()
        if item.get("role_status") == "active"
    }
    if name.lower() in active_names:
        return blocked("active_role_name_must_be_unique")
    known_ids = {
        str(item.get("role_id"))
        for item in current_roles()
        if item.get("role_status") == "active"
    }
    if any(item not in known_ids for item in inherited):
        return blocked("inherited_role_required")
    definition = {
        "name": name,
        "description": str(description or "").strip(),
        "permissions": permission_set,
        "inherits_role_ids": inherited,
    }
    content = {
        "event_type": "role_defined",
        "definition": definition,
        "definition_sha256": _sha(definition),
        "reason": reason,
        "revision": 1,
        "supersedes_role_id": None,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "role_id": f"role-{digest[:24]}",
        "policy_event_id": f"policy-event-{digest[:24]}",
        "policy_event_sha256": digest,
        "policy_records_mutated": False,
        "case_access_scope_changed": False,
    }
    result = _record(ACTIONS[0], event, actor, name, ip_address)
    return {
        **result,
        "status": "role_defined",
        "next_action": "review_permission_matrix",
    }


def revise_role(
    role_id: str,
    *,
    actor: str,
    name: str,
    permissions: Any,
    inherits_role_ids: Any,
    description: str,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    previous = find_role(role_id)
    if previous is None or previous.get("role_status") != "active":
        return blocked("active_role_required")
    if confirmed is not True:
        return blocked("explicit_role_revision_confirmation_required")
    reason = str(reason or "").strip()
    if not reason:
        return blocked("administrative_reason_required")
    permission_set = sorted(
        {str(item) for item in (permissions or []) if str(item) in PERMISSIONS}
    )
    if len(permission_set) != len(
        {str(item) for item in (permissions or []) if str(item)}
    ):
        return blocked("permission_invalid")
    inherited = sorted({str(item) for item in (inherits_role_ids or []) if str(item)})
    if role_id in inherited:
        return blocked("role_cannot_inherit_itself")
    active_ids = {
        str(item.get("role_id"))
        for item in current_roles()
        if item.get("role_status") == "active" and item.get("role_id") != role_id
    }
    if any(item not in active_ids for item in inherited):
        return blocked("inherited_role_required")
    definition = {
        "name": str(name or previous.get("definition", {}).get("name") or "").strip(),
        "description": str(description or "").strip(),
        "permissions": permission_set,
        "inherits_role_ids": inherited,
    }
    binding = {
        "role_id": role_id,
        "policy_event_id": previous.get("policy_event_id"),
        "policy_event_sha256": previous.get("policy_event_sha256"),
        "definition_sha256": previous.get("definition_sha256"),
        "revision": previous.get("revision"),
    }
    content = {
        "event_type": "role_revised",
        "definition": definition,
        "definition_sha256": _sha(definition),
        "reason": reason,
        "revision": int(previous.get("revision") or 1) + 1,
        "supersedes_role_id": role_id,
        "previous_role_binding": binding,
        "previous_role_binding_sha256": _sha(binding),
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "role_id": f"role-{digest[:24]}",
        "policy_event_id": f"policy-event-{digest[:24]}",
        "policy_event_sha256": digest,
        "prior_role_event_mutated": False,
        "case_access_scope_changed": False,
    }
    result = _record(ACTIONS[1], event, actor, definition["name"], ip_address)
    return {
        **result,
        "status": "role_revised",
        "next_action": "review_permission_matrix",
    }


def create_case_access_rule(
    *,
    actor: str,
    subject_type: str,
    subject_id: str,
    case_id: str,
    permissions: Any,
    effect: str,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    subject_type = str(subject_type or "").strip()
    subject_id = str(subject_id or "").strip()
    case_id = str(case_id or "").strip()
    effect = str(effect or "allow").strip()
    reason = str(reason or "").strip()
    permission_set = sorted(
        {str(item) for item in (permissions or []) if str(item) in PERMISSIONS}
    )
    if confirmed is not True:
        return blocked("explicit_access_rule_confirmation_required")
    if subject_type not in {"user", "role"}:
        return blocked("subject_type_invalid")
    if not subject_id or not case_id:
        return blocked("subject_and_case_required")
    if effect not in EFFECTS:
        return blocked("access_effect_invalid")
    if not permission_set:
        return blocked("permission_required")
    if not reason:
        return blocked("administrative_reason_required")
    if subject_type == "role" and (
        find_role(subject_id) is None
        or find_role(subject_id).get("role_status") != "active"
    ):
        return blocked("active_role_required")
    definition = {
        "subject_type": subject_type,
        "subject_id": subject_id,
        "case_id": case_id,
        "permissions": permission_set,
        "effect": effect,
    }
    content = {
        "event_type": "case_access_granted"
        if effect == "allow"
        else "case_access_denied",
        "definition": definition,
        "definition_sha256": _sha(definition),
        "reason": reason,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "access_rule_id": f"access-rule-{digest[:24]}",
        "policy_event_id": f"policy-event-{digest[:24]}",
        "policy_event_sha256": digest,
        "explicit_deny_overrides_allow": True,
        "case_access_scope_changed": True,
    }
    action = ACTIONS[2] if effect == "allow" else ACTIONS[3]
    result = _record(
        action, event, actor, f"{subject_type}:{subject_id}:{case_id}", ip_address
    )
    return {
        **result,
        "status": "case_access_rule_created",
        "next_action": "evaluate_effective_access",
    }


def revoke_case_access_rule(
    access_rule_id: str,
    *,
    actor: str,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    rule = next(
        (
            item
            for item in current_access_rules()
            if item.get("access_rule_id") == access_rule_id
        ),
        None,
    )
    if rule is None or rule.get("rule_status") != "active":
        return blocked("active_access_rule_required")
    if confirmed is not True:
        return blocked("explicit_access_revocation_confirmation_required")
    reason = str(reason or "").strip()
    if not reason:
        return blocked("administrative_reason_required")
    binding = {
        "access_rule_id": access_rule_id,
        "policy_event_id": rule.get("policy_event_id"),
        "policy_event_sha256": rule.get("policy_event_sha256"),
        "definition_sha256": rule.get("definition_sha256"),
    }
    content = {
        "event_type": "case_access_revoked",
        "revoked_access_rule_id": access_rule_id,
        "access_rule_binding": binding,
        "access_rule_binding_sha256": _sha(binding),
        "reason": reason,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "policy_event_id": f"policy-event-{digest[:24]}",
        "policy_event_sha256": digest,
        "prior_access_rule_mutated": False,
        "case_access_scope_changed": True,
    }
    result = _record(ACTIONS[4], event, actor, access_rule_id, ip_address)
    return {
        **result,
        "status": "case_access_rule_revoked",
        "next_action": "evaluate_effective_access",
    }
