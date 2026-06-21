from __future__ import annotations

from collections import Counter
from typing import Any

from . import database
from .dossier_assembly_workspace_v21_0 import _sha
from .access_policy_events_v28_2 import (
    PERMISSIONS,
    SCHEMA,
    VERSION,
    current_access_rules,
    current_roles,
    history,
)


def _active_roles_by_id() -> dict[str, dict[str, Any]]:
    return {
        str(item.get("role_id")): item
        for item in current_roles()
        if item.get("role_status") == "active"
    }


def resolve_role_permissions(role_id: str) -> dict[str, Any]:
    roles = _active_roles_by_id()
    visited: set[str] = set()
    stack: set[str] = set()
    inherited_from: list[str] = []
    cycle_detected = False

    def walk(current_id: str) -> set[str]:
        nonlocal cycle_detected
        if current_id in stack:
            cycle_detected = True
            return set()
        if current_id in visited:
            return set()
        role = roles.get(current_id)
        if role is None:
            return set()
        visited.add(current_id)
        stack.add(current_id)
        definition = role.get("definition") or {}
        result = set(str(item) for item in definition.get("permissions") or [])
        for parent_id in definition.get("inherits_role_ids") or []:
            inherited_from.append(str(parent_id))
            result.update(walk(str(parent_id)))
        stack.remove(current_id)
        return result

    permissions = sorted(walk(role_id))
    return {
        "role_id": role_id,
        "effective_permissions": permissions,
        "effective_permission_count": len(permissions),
        "inherited_from_role_ids": sorted(set(inherited_from)),
        "inheritance_cycle_detected": cycle_detected,
        "resolution_sha256": _sha(
            {
                "role_id": role_id,
                "permissions": permissions,
                "parents": sorted(set(inherited_from)),
            }
        ),
    }


def _users() -> list[dict[str, Any]]:
    database.ensure_configured()
    session = database.Session()
    try:
        rows = session.query(database.User).order_by(database.User.username.asc()).all()
        return [
            {
                "username": row.username,
                "role": row.role,
                "is_admin": bool(row.is_admin),
                "is_active": bool(row.is_active),
            }
            for row in rows
        ]
    finally:
        session.close()


def evaluate_effective_access(username: str, case_id: str) -> dict[str, Any]:
    user = next((item for item in _users() if item.get("username") == username), None)
    if user is None:
        return {
            "status": "user_not_found",
            "username": username,
            "case_id": case_id,
            "effective_permissions": [],
            "explicit_denies": [],
            "explicit_allows": [],
            "deny_overrides_allow": True,
        }
    roles = _active_roles_by_id()
    role = next(
        (
            item
            for item in roles.values()
            if str((item.get("definition") or {}).get("name") or "").lower()
            == str(user.get("role") or "").lower()
        ),
        None,
    )
    base_permissions: set[str] = set()
    role_id = None
    role_resolution = None
    if role:
        role_id = str(role.get("role_id"))
        role_resolution = resolve_role_permissions(role_id)
        base_permissions.update(role_resolution["effective_permissions"])

    allows: set[str] = set()
    denies: set[str] = set()
    applied_rule_ids: list[str] = []
    for rule in current_access_rules():
        if rule.get("rule_status") != "active":
            continue
        definition = rule.get("definition") or {}
        if str(definition.get("case_id") or "") != str(case_id):
            continue
        subject_type = definition.get("subject_type")
        subject_id = str(definition.get("subject_id") or "")
        applies = subject_type == "user" and subject_id == username
        applies = applies or (
            subject_type == "role" and role_id and subject_id == role_id
        )
        if not applies:
            continue
        applied_rule_ids.append(str(rule.get("access_rule_id")))
        target = denies if definition.get("effect") == "deny" else allows
        target.update(str(item) for item in definition.get("permissions") or [])

    effective = (base_permissions | allows) - denies
    return {
        "status": "ready",
        "username": username,
        "case_id": case_id,
        "assigned_role": user.get("role"),
        "resolved_role_id": role_id,
        "role_resolution": role_resolution,
        "base_permissions": sorted(base_permissions),
        "explicit_allows": sorted(allows),
        "explicit_denies": sorted(denies),
        "effective_permissions": sorted(effective),
        "effective_permission_count": len(effective),
        "applied_access_rule_ids": sorted(applied_rule_ids),
        "deny_overrides_allow": True,
        "evaluation_sha256": _sha(
            {
                "username": username,
                "case_id": case_id,
                "base": sorted(base_permissions),
                "allows": sorted(allows),
                "denies": sorted(denies),
                "effective": sorted(effective),
            }
        ),
        "access_view_grants_access": False,
    }


def _least_privilege_findings(
    roles: list[dict[str, Any]], rules: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    findings = []
    for role in roles:
        if role.get("role_status") != "active":
            continue
        role_id = str(role.get("role_id"))
        definition = role.get("definition") or {}
        resolved = resolve_role_permissions(role_id)
        name = str(definition.get("name") or "")
        if resolved["inheritance_cycle_detected"]:
            findings.append(
                {
                    "severity": "high",
                    "key": "role_inheritance_cycle",
                    "role_id": role_id,
                    "role_name": name,
                }
            )
        if resolved["effective_permission_count"] >= 12 and name.lower() != "admin":
            findings.append(
                {
                    "severity": "medium",
                    "key": "broad_non_admin_role",
                    "role_id": role_id,
                    "role_name": name,
                    "permission_count": resolved["effective_permission_count"],
                }
            )
        if "administration.read" in resolved[
            "effective_permissions"
        ] and name.lower() not in {"admin", "supervisor"}:
            findings.append(
                {
                    "severity": "medium",
                    "key": "administration_permission_on_non_privileged_role",
                    "role_id": role_id,
                    "role_name": name,
                }
            )
    duplicates = Counter(
        (
            (rule.get("definition") or {}).get("subject_type"),
            (rule.get("definition") or {}).get("subject_id"),
            (rule.get("definition") or {}).get("case_id"),
            (rule.get("definition") or {}).get("effect"),
            tuple((rule.get("definition") or {}).get("permissions") or []),
        )
        for rule in rules
        if rule.get("rule_status") == "active"
    )
    for key, count in duplicates.items():
        if count > 1:
            findings.append(
                {
                    "severity": "low",
                    "key": "duplicate_active_access_rule",
                    "rule_signature": list(key[:-1]) + [list(key[-1])],
                    "count": count,
                }
            )
    return findings


def build_access_policy_workspace() -> dict[str, Any]:
    roles = current_roles()
    rules = current_access_rules()
    active_roles = [item for item in roles if item.get("role_status") == "active"]
    active_rules = [item for item in rules if item.get("rule_status") == "active"]
    matrix = [
        {
            **resolve_role_permissions(str(item.get("role_id"))),
            "name": (item.get("definition") or {}).get("name"),
            "direct_permissions": (item.get("definition") or {}).get("permissions")
            or [],
        }
        for item in active_roles
    ]
    findings = _least_privilege_findings(roles, rules)
    events = history()
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "ready",
        "permission_catalog": list(PERMISSIONS),
        "roles": roles,
        "active_roles": active_roles,
        "role_count": len(roles),
        "active_role_count": len(active_roles),
        "permission_matrix": matrix,
        "access_rules": rules,
        "active_access_rules": active_rules,
        "access_rule_count": len(rules),
        "active_access_rule_count": len(active_rules),
        "explicit_deny_rule_count": sum(
            (item.get("definition") or {}).get("effect") == "deny"
            for item in active_rules
        ),
        "least_privilege_findings": findings,
        "least_privilege_finding_count": len(findings),
        "access_policy_history": events[-200:],
        "access_policy_event_count": len(events),
        "explicit_deny_overrides_allow": True,
        "access_views_grant_access": False,
        "case_access_scope_changed_by_view": False,
        "next_action": "review_role_and_access_policy",
    }
