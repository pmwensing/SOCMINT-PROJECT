from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Any

from . import database as db

SCHEMA = "socmint.case_adapter_control.v39_3"
VERSION = "v39.3.0"
ADAPTER_KEY = "46_montreal_street"
CANONICAL_CASE_ID = "46MONST"

_SYSTEM_MODE_ACTION = "case_adapter_system_mode_changed"
_CASE_MODE_ACTION = "case_adapter_mode_changed"


class AdapterMode(str, Enum):
    OFF = "off"
    PASSIVE = "passive"
    ON = "on"


_MODE_RANK = {
    AdapterMode.OFF: 0,
    AdapterMode.PASSIVE: 1,
    AdapterMode.ON: 2,
}

_CASE_ALIASES = {
    "46",
    "46monst",
    "46-montreal-street",
    "46_montreal_street",
    "46 montreal street",
    "46 montreal st",
}

CASE_SCOPE = {
    "pre_fire_proceeding": True,
    "post_fire_lockout_proceeding": True,
    "cowdy_street": {
        "upstairs_noise": True,
        "water_leak": True,
        "other_issues": False,
        "landlord_adverse_characterization": False,
    },
}

_PASSIVE_OPERATIONS = {
    "inventory",
    "validate",
    "prepare_import",
    "claim_proof_projection",
    "timeline_projection",
    "scope_compliance_report",
}

_ON_ONLY_OPERATIONS = {
    "execute_controlled_import",
}

_ALWAYS_FORBIDDEN_OPERATIONS = {
    "assign_truth",
    "approve_claim",
    "merge_entity",
    "mutate_dossier",
    "publish",
    "submit_evidence",
    "trigger_public_web_collection",
}


def _required(value: Any, field: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field} is required")
    return normalized


def _mode(value: AdapterMode | str) -> AdapterMode:
    try:
        return value if isinstance(value, AdapterMode) else AdapterMode(str(value).strip().lower())
    except ValueError as exc:
        raise ValueError("mode must be one of: off, passive, on") from exc


def _canonical_case_id(value: Any) -> str:
    normalized = _required(value, "case_id").strip().lower()
    if normalized not in _CASE_ALIASES:
        raise ValueError("46 Montreal Street adapter is restricted to case 46MONST")
    return CANONICAL_CASE_ID


def _valid_sha256(value: Any) -> bool:
    normalized = str(value or "").strip().lower()
    return len(normalized) == 64 and all(char in "0123456789abcdef" for char in normalized)


def _details(row: Any) -> dict[str, Any]:
    try:
        payload = json.loads(row.details or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _latest_system_mode() -> tuple[AdapterMode, dict[str, Any]]:
    db.ensure_configured()
    session = db.Session()
    try:
        rows = (
            session.query(db.AuditLog)
            .filter_by(action=_SYSTEM_MODE_ACTION)
            .order_by(db.AuditLog.id.desc())
            .all()
        )
    finally:
        session.close()
    for row in rows:
        details = _details(row)
        if details.get("adapter") == ADAPTER_KEY:
            try:
                return _mode(details.get("new_mode")), details
            except ValueError:
                continue
    return AdapterMode.PASSIVE, {
        "adapter": ADAPTER_KEY,
        "new_mode": AdapterMode.PASSIVE.value,
        "defaulted": True,
    }


def _latest_case_mode(case_id: str) -> tuple[AdapterMode, dict[str, Any]]:
    db.ensure_configured()
    session = db.Session()
    try:
        rows = (
            session.query(db.AuditLog)
            .filter_by(action=_CASE_MODE_ACTION)
            .order_by(db.AuditLog.id.desc())
            .all()
        )
    finally:
        session.close()
    for row in rows:
        details = _details(row)
        if details.get("adapter") == ADAPTER_KEY and details.get("case_id") == case_id:
            try:
                return _mode(details.get("new_mode")), details
            except ValueError:
                continue
    return AdapterMode.PASSIVE, {
        "adapter": ADAPTER_KEY,
        "case_id": case_id,
        "new_mode": AdapterMode.PASSIVE.value,
        "defaulted": True,
    }


def effective_mode(
    *,
    system_maximum: AdapterMode | str,
    case_mode: AdapterMode | str,
    requested_mode: AdapterMode | str,
) -> AdapterMode:
    candidates = [_mode(system_maximum), _mode(case_mode), _mode(requested_mode)]
    return min(candidates, key=lambda item: _MODE_RANK[item])


def permissions_for_mode(mode: AdapterMode | str) -> dict[str, bool]:
    normalized = _mode(mode)
    permissions = {
        operation: normalized in {AdapterMode.PASSIVE, AdapterMode.ON}
        for operation in sorted(_PASSIVE_OPERATIONS)
    }
    permissions.update(
        {
            operation: normalized is AdapterMode.ON
            for operation in sorted(_ON_ONLY_OPERATIONS)
        }
    )
    permissions.update({operation: False for operation in sorted(_ALWAYS_FORBIDDEN_OPERATIONS)})
    return permissions


def get_adapter_state(
    case_id: Any = CANONICAL_CASE_ID,
    *,
    requested_mode: AdapterMode | str | None = None,
) -> dict[str, Any]:
    canonical_case_id = _canonical_case_id(case_id)
    system_mode, system_event = _latest_system_mode()
    case_mode, case_event = _latest_case_mode(canonical_case_id)
    requested = case_mode if requested_mode is None else _mode(requested_mode)
    effective = effective_mode(
        system_maximum=system_mode,
        case_mode=case_mode,
        requested_mode=requested,
    )
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "adapter": ADAPTER_KEY,
        "case_id": canonical_case_id,
        "system_maximum_mode": system_mode.value,
        "case_mode": case_mode.value,
        "requested_mode": requested.value,
        "effective_mode": effective.value,
        "active_import_plan_sha256": case_event.get("import_plan_sha256"),
        "permissions": permissions_for_mode(effective),
        "scope": CASE_SCOPE,
        "system_control": system_event,
        "case_control": case_event,
        "authoritative_case_records_changed": False,
    }


def set_system_maximum_mode(
    mode: AdapterMode | str,
    *,
    actor: str,
    reason: str,
    confirmed: bool = False,
) -> dict[str, Any]:
    normalized = _mode(mode)
    actor = _required(actor, "actor")
    reason = _required(reason, "reason")
    previous, _ = _latest_system_mode()
    if normalized is AdapterMode.ON and confirmed is not True:
        raise ValueError("system on mode requires explicit confirmation")
    if normalized is previous:
        return {
            "schema": SCHEMA,
            "changed": False,
            "previous_mode": previous.value,
            "new_mode": normalized.value,
        }
    db.record_audit_event(
        action=_SYSTEM_MODE_ACTION,
        actor=actor,
        details={
            "schema": SCHEMA,
            "adapter": ADAPTER_KEY,
            "previous_mode": previous.value,
            "new_mode": normalized.value,
            "reason": reason,
            "confirmed": confirmed is True,
            "authoritative_case_records_changed": False,
        },
    )
    return {
        "schema": SCHEMA,
        "changed": True,
        "previous_mode": previous.value,
        "new_mode": normalized.value,
    }


def set_case_adapter_mode(
    case_id: Any,
    mode: AdapterMode | str,
    *,
    actor: str,
    reason: str,
    confirmed: bool = False,
    import_plan_sha256: str | None = None,
) -> dict[str, Any]:
    canonical_case_id = _canonical_case_id(case_id)
    normalized = _mode(mode)
    actor = _required(actor, "actor")
    reason = _required(reason, "reason")
    previous, previous_event = _latest_case_mode(canonical_case_id)

    if previous is AdapterMode.OFF and normalized is AdapterMode.ON:
        raise ValueError("off to on is prohibited; switch to passive and review a preview first")
    if normalized is AdapterMode.ON:
        if confirmed is not True:
            raise ValueError("on mode requires explicit operator confirmation")
        if not _valid_sha256(import_plan_sha256):
            raise ValueError("on mode requires an approved import_plan_sha256")
    if normalized is previous:
        active_hash = previous_event.get("import_plan_sha256")
        if normalized is not AdapterMode.ON or active_hash == str(import_plan_sha256).lower():
            return {
                "schema": SCHEMA,
                "changed": False,
                "previous_mode": previous.value,
                "new_mode": normalized.value,
                "import_plan_sha256": active_hash,
            }

    event_details = {
        "schema": SCHEMA,
        "adapter": ADAPTER_KEY,
        "case_id": canonical_case_id,
        "previous_mode": previous.value,
        "new_mode": normalized.value,
        "reason": reason,
        "confirmed": confirmed is True,
        "import_plan_sha256": (
            str(import_plan_sha256).strip().lower()
            if normalized is AdapterMode.ON
            else None
        ),
        "scope_sha256": hashlib.sha256(
            json.dumps(CASE_SCOPE, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "authoritative_case_records_changed": False,
    }
    db.record_audit_event(
        action=_CASE_MODE_ACTION,
        actor=actor,
        details=event_details,
    )
    return {
        "schema": SCHEMA,
        "changed": True,
        "previous_mode": previous.value,
        "new_mode": normalized.value,
        "import_plan_sha256": event_details["import_plan_sha256"],
    }


def authorize_operation(
    case_id: Any,
    operation: str,
    *,
    requested_mode: AdapterMode | str | None = None,
    confirmed: bool = False,
    import_plan_sha256: str | None = None,
) -> dict[str, Any]:
    operation = _required(operation, "operation")
    state = get_adapter_state(case_id, requested_mode=requested_mode)
    permissions = state["permissions"]
    if operation not in permissions:
        return {
            "schema": SCHEMA,
            "status": "blocked",
            "operation": operation,
            "effective_mode": state["effective_mode"],
            "blocker": "unknown_operation",
            "authoritative_case_records_changed": False,
        }
    if permissions[operation] is not True:
        return {
            "schema": SCHEMA,
            "status": "blocked",
            "operation": operation,
            "effective_mode": state["effective_mode"],
            "blocker": "operation_not_permitted_in_effective_mode",
            "authoritative_case_records_changed": False,
        }
    if operation == "execute_controlled_import":
        active_hash = state.get("active_import_plan_sha256")
        supplied_hash = str(import_plan_sha256 or "").strip().lower()
        if confirmed is not True:
            return {
                "schema": SCHEMA,
                "status": "blocked",
                "operation": operation,
                "effective_mode": state["effective_mode"],
                "blocker": "explicit_execution_confirmation_required",
                "authoritative_case_records_changed": False,
            }
        if not active_hash or supplied_hash != active_hash:
            return {
                "schema": SCHEMA,
                "status": "blocked",
                "operation": operation,
                "effective_mode": state["effective_mode"],
                "blocker": "approved_import_plan_binding_required",
                "authoritative_case_records_changed": False,
            }
    return {
        "schema": SCHEMA,
        "status": "allowed",
        "operation": operation,
        "effective_mode": state["effective_mode"],
        "import_plan_sha256": state.get("active_import_plan_sha256"),
        "authoritative_case_records_changed": False,
    }


def passive_report_footer() -> str:
    return "No authoritative case records were changed."
