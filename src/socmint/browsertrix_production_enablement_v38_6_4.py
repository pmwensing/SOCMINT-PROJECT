from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlsplit

from . import database
from .dossier_assembly_workspace_v21_0 import (
    _canonical,
    _ensure_storage,
    _json_details,
    _sha,
)

SCHEMA = "socmint.browsertrix_production_enablement.v38_6_4"
VERSION = "v38.6.4"
ISSUE_ACTION = "browsertrix_production_enablement_issued"
CLAIM_ACTION = "browsertrix_production_enablement_claimed"
REVOKE_ACTION = "browsertrix_production_enablement_revoked"
ACTIONS = (ISSUE_ACTION, CLAIM_ACTION, REVOKE_ACTION)
MAX_ENABLEMENT_DURATION = timedelta(hours=24)


def _required(value: Any) -> str:
    return str(value or "").strip()


def _time(value: Any) -> datetime | None:
    raw = _required(value)
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _host(url: Any) -> str:
    try:
        return (urlsplit(_required(url)).hostname or "").lower().rstrip(".")
    except ValueError:
        return ""


def blocked(key: str, **details: Any) -> dict[str, Any]:
    result = {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key}],
        "production_enablement_granted": False,
        "production_execution_authorized": False,
        "runtime_execution_performed": False,
        "automatic_retry_performed": False,
        "artifact_registered": False,
        "source_registered": False,
        "import_registered": False,
        "observation_created": False,
        "truth_assigned": False,
        "entity_merged": False,
        "claim_approved": False,
        "dossier_mutated": False,
        "export_created": False,
        "published": False,
    }
    if details:
        result["details"] = details
    return result


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
                "recorded_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    finally:
        session.close()


def _record(
    action: str,
    actor: str,
    target: str,
    event: dict[str, Any],
    ip_address: str | None,
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
            "recorded_at": row.created_at.isoformat() if row.created_at else None,
        }
    finally:
        session.close()


def current_enablements() -> list[dict[str, Any]]:
    current: dict[str, dict[str, Any]] = {}
    for event in history():
        enablement_id = _required(event.get("production_enablement_id"))
        if not enablement_id:
            continue
        if event.get("event_type") == ISSUE_ACTION:
            current[enablement_id] = {
                **event,
                "enablement_state": "active",
                "claim_event": None,
                "revocation_event": None,
            }
        elif event.get("event_type") == CLAIM_ACTION and enablement_id in current:
            current[enablement_id] = {
                **current[enablement_id],
                "enablement_state": "claimed",
                "claim_event": event,
            }
        elif event.get("event_type") == REVOKE_ACTION and enablement_id in current:
            current[enablement_id] = {
                **current[enablement_id],
                "enablement_state": "revoked",
                "revocation_event": event,
            }
    return sorted(
        current.values(),
        key=lambda item: str(item.get("recorded_at") or ""),
        reverse=True,
    )


def find_enablement(production_enablement_id: str) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in current_enablements()
            if item.get("production_enablement_id") == production_enablement_id
        ),
        None,
    )


def _limits_are_not_broader(
    production: dict[str, Any], certification: dict[str, Any]
) -> bool:
    numeric_limits = {
        "max_pages",
        "max_depth",
        "max_duration_seconds",
        "max_download_bytes",
        "max_redirects",
        "navigation_timeout_seconds",
        "max_screenshots",
        "concurrency",
    }
    try:
        return all(
            int(production.get(key)) <= int(certification.get(key))
            for key in numeric_limits
        )
    except (TypeError, ValueError):
        return False


def issue_production_enablement(
    *,
    actor: str,
    certification_plan: dict[str, Any] | None,
    certification_result: dict[str, Any] | None,
    production_execution_plan: dict[str, Any] | None,
    deployment_policy: dict[str, Any] | None,
    deployment_id: str,
    issued_at: str,
    valid_from: str,
    expires_at: str,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    if confirmed is not True:
        return blocked("explicit_production_enablement_confirmation_required")
    actor = _required(actor)
    deployment_id = _required(deployment_id)
    reason = _required(reason)
    if not actor:
        return blocked("actor_required")
    if not deployment_id:
        return blocked("deployment_id_required")
    if not reason:
        return blocked("administrative_reason_required")
    if not isinstance(certification_plan, dict) or certification_plan.get(
        "status"
    ) != "browsertrix_deployment_certification_prepared":
        return blocked("prepared_deployment_certification_required")
    if not isinstance(certification_result, dict) or certification_result.get(
        "status"
    ) != "browsertrix_deployment_certification_passed":
        return blocked("passing_deployment_certification_required")
    if certification_result.get("production_enablement_granted") is not False:
        return blocked("certification_must_not_self_enable_production")
    if not all(
        value is True
        for value in (certification_result.get("required_proofs") or {}).values()
    ):
        return blocked("complete_certification_proof_set_required")

    evidence = certification_result.get("evidence") or {}
    exact_certification_bindings = {
        "plan_id": evidence.get("certification_plan_id")
        == certification_plan.get("certification_plan_id"),
        "plan_sha256": evidence.get("certification_plan_sha256")
        == certification_plan.get("certification_plan_sha256"),
        "runtime_request_id": evidence.get("runtime_request_id")
        == certification_plan.get("runtime_request_id"),
        "runtime_sha256": evidence.get("runtime_sha256")
        == certification_plan.get("runtime_sha256"),
    }
    if not all(exact_certification_bindings.values()):
        return blocked(
            "certification_result_binding_mismatch",
            exact_certification_bindings=exact_certification_bindings,
        )

    if not isinstance(production_execution_plan, dict) or production_execution_plan.get(
        "status"
    ) != "browsertrix_execution_prepared":
        return blocked("prepared_production_execution_plan_required")
    if not isinstance(deployment_policy, dict):
        return blocked("production_deployment_policy_required")
    if deployment_policy.get("execution_mode") != "production":
        return blocked("production_execution_mode_required")
    if deployment_policy.get("runtime_enabled") is not True:
        return blocked("production_runtime_must_be_explicitly_enabled")
    if deployment_policy.get("operator_confirmed") is not True:
        return blocked("production_operator_confirmation_required")
    if _required(deployment_policy.get("deployment_id")) != deployment_id:
        return blocked("deployment_policy_identity_mismatch")

    certified_runtime = certification_plan.get("runtime_request") or {}
    certified_plan = certified_runtime.get("execution_plan") or {}
    certified_request = certified_plan.get("prepared_request") or {}
    production_request = production_execution_plan.get("prepared_request") or {}
    case_id = _required(production_request.get("case_id"))
    approved_domain = _required(production_execution_plan.get("approved_domain"))
    requested_host = _host(production_execution_plan.get("requested_url"))
    if not case_id or not approved_domain or requested_host != approved_domain:
        return blocked("production_case_and_domain_scope_required")
    if approved_domain.endswith(".test") or approved_domain.endswith(".invalid"):
        return blocked("fictional_domain_not_eligible_for_production")

    certified_limits = certified_request.get("resource_limits") or {}
    production_limits = production_request.get("resource_limits") or {}
    if not _limits_are_not_broader(production_limits, certified_limits):
        return blocked("production_resource_limits_exceed_certification")

    certified_storage = certified_runtime.get("storage") or {}
    intended_scope = {
        "deployment_id": deployment_id,
        "case_id": case_id,
        "approved_domain": approved_domain,
        "production_execution_plan_id": production_execution_plan.get(
            "execution_plan_id"
        ),
        "production_execution_plan_sha256": production_execution_plan.get(
            "execution_plan_sha256"
        ),
        "runtime": deployment_policy.get("runtime"),
        "image_digest": deployment_policy.get("image_digest"),
        "network_name": deployment_policy.get("network_name"),
        "approved_storage_root": deployment_policy.get("approved_storage_root"),
        "resource_limits": production_limits,
    }
    certified_infrastructure = {
        "runtime": certified_runtime.get("runtime"),
        "image_digest": certified_runtime.get("image_digest"),
        "network_name": certified_runtime.get("network_name"),
        "approved_storage_root": certified_storage.get("approved_root"),
    }
    infrastructure_matches = {
        key: intended_scope.get(key) == value
        for key, value in certified_infrastructure.items()
    }
    if not all(infrastructure_matches.values()):
        return blocked(
            "production_infrastructure_exceeds_certification",
            infrastructure_matches=infrastructure_matches,
        )
    if deployment_policy.get("execution_plan_sha256") != intended_scope.get(
        "production_execution_plan_sha256"
    ):
        return blocked("production_execution_plan_policy_mismatch")

    issued = _time(issued_at)
    start = _time(valid_from)
    end = _time(expires_at)
    if issued is None or start is None or end is None:
        return blocked("enablement_times_invalid")
    if start < issued or end <= start or end - start > MAX_ENABLEMENT_DURATION:
        return blocked("enablement_window_invalid")

    certification_binding = {
        "certification_id": certification_result.get("certification_id"),
        "certification_sha256": certification_result.get("certification_sha256"),
        "certification_plan_id": certification_plan.get("certification_plan_id"),
        "certification_plan_sha256": certification_plan.get(
            "certification_plan_sha256"
        ),
        "runtime_request_id": certification_plan.get("runtime_request_id"),
        "runtime_sha256": certification_plan.get("runtime_sha256"),
    }
    definition = {
        "deployment_id": deployment_id,
        "issued_at": issued.isoformat(),
        "valid_from": start.isoformat(),
        "expires_at": end.isoformat(),
        "certification_binding": certification_binding,
        "certification_binding_sha256": _sha(certification_binding),
        "authorized_scope": intended_scope,
        "authorized_scope_sha256": _sha(intended_scope),
        "single_use": True,
        "operator_action_required": True,
        "automatic_execution": False,
        "automatic_retry": False,
        "reason": reason,
    }
    digest = _sha(definition)
    enablement_id = f"browsertrix-production-enablement-{digest[:24]}"
    existing = find_enablement(enablement_id)
    if existing is not None:
        return {
            **existing,
            "status": "browsertrix_production_enablement_reused",
            "idempotent_replay": True,
            "next_action": "claim_production_enablement_for_execution",
        }

    event = {
        "schema": SCHEMA,
        "version": VERSION,
        "event_type": ISSUE_ACTION,
        "production_enablement_id": enablement_id,
        "production_enablement_sha256": digest,
        "definition": definition,
        "production_enablement_granted": True,
        "production_execution_authorized": False,
        "runtime_execution_performed": False,
        "automatic_retry_performed": False,
        "artifact_registered": False,
        "source_registered": False,
        "import_registered": False,
        "observation_created": False,
        "truth_assigned": False,
        "entity_merged": False,
        "claim_approved": False,
        "dossier_mutated": False,
        "export_created": False,
        "published": False,
    }
    result = _record(ISSUE_ACTION, actor, enablement_id, event, ip_address)
    return {
        **result,
        "status": "browsertrix_production_enablement_issued",
        "idempotent_replay": False,
        "next_action": "claim_production_enablement_for_execution",
    }


def claim_production_enablement(
    *,
    actor: str,
    production_enablement_id: str,
    production_enablement_sha256: str,
    production_execution_plan: dict[str, Any] | None,
    claimed_at: str,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    if confirmed is not True:
        return blocked("explicit_production_execution_claim_confirmation_required")
    actor = _required(actor)
    enablement_id = _required(production_enablement_id)
    reason = _required(reason)
    if not actor:
        return blocked("actor_required")
    if not reason:
        return blocked("administrative_reason_required")
    enablement = find_enablement(enablement_id)
    if enablement is None:
        return blocked("production_enablement_required")
    if enablement.get("enablement_state") != "active":
        return blocked("active_unclaimed_production_enablement_required")
    if enablement.get("production_enablement_sha256") != _required(
        production_enablement_sha256
    ):
        return blocked("production_enablement_hash_mismatch")
    if not isinstance(production_execution_plan, dict) or production_execution_plan.get(
        "status"
    ) != "browsertrix_execution_prepared":
        return blocked("prepared_production_execution_plan_required")

    definition = enablement.get("definition") or {}
    scope = definition.get("authorized_scope") or {}
    if production_execution_plan.get("execution_plan_id") != scope.get(
        "production_execution_plan_id"
    ) or production_execution_plan.get("execution_plan_sha256") != scope.get(
        "production_execution_plan_sha256"
    ):
        return blocked("claimed_execution_plan_outside_enablement_scope")
    claimed = _time(claimed_at)
    start = _time(definition.get("valid_from"))
    end = _time(definition.get("expires_at"))
    if claimed is None or start is None or end is None or not (start <= claimed < end):
        return blocked("production_enablement_not_valid_at_claim_time")

    authorization = {
        "production_enablement_id": enablement_id,
        "production_enablement_sha256": enablement.get(
            "production_enablement_sha256"
        ),
        "deployment_id": scope.get("deployment_id"),
        "case_id": scope.get("case_id"),
        "approved_domain": scope.get("approved_domain"),
        "production_execution_plan_id": scope.get("production_execution_plan_id"),
        "production_execution_plan_sha256": scope.get(
            "production_execution_plan_sha256"
        ),
        "runtime": scope.get("runtime"),
        "image_digest": scope.get("image_digest"),
        "network_name": scope.get("network_name"),
        "approved_storage_root": scope.get("approved_storage_root"),
        "authorized_resource_limits": scope.get("resource_limits"),
        "claimed_at": claimed.isoformat(),
        "expires_at": definition.get("expires_at"),
        "single_use": True,
        "automatic_execution": False,
        "automatic_retry": False,
    }
    authorization_sha256 = _sha(authorization)
    content = {
        "event_type": CLAIM_ACTION,
        "production_enablement_id": enablement_id,
        "production_enablement_sha256": enablement.get(
            "production_enablement_sha256"
        ),
        "runtime_authorization": authorization,
        "runtime_authorization_sha256": authorization_sha256,
        "reason": reason,
        "production_enablement_granted": True,
        "production_execution_authorized": True,
        "runtime_execution_performed": False,
        "automatic_retry_performed": False,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "production_enablement_event_id": f"browsertrix-enablement-event-{digest[:24]}",
        "production_enablement_event_sha256": digest,
    }
    result = _record(CLAIM_ACTION, actor, enablement_id, event, ip_address)
    return {
        **result,
        "status": "browsertrix_production_execution_authorized",
        "next_action": "prepare_certification_bound_container_runtime",
    }


def revoke_production_enablement(
    *,
    actor: str,
    production_enablement_id: str,
    production_enablement_sha256: str,
    revoked_at: str,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    if confirmed is not True:
        return blocked("explicit_production_enablement_revocation_required")
    actor = _required(actor)
    enablement_id = _required(production_enablement_id)
    reason = _required(reason)
    if not actor:
        return blocked("actor_required")
    if not reason:
        return blocked("administrative_reason_required")
    enablement = find_enablement(enablement_id)
    if enablement is None:
        return blocked("production_enablement_required")
    if enablement.get("enablement_state") == "revoked":
        return {
            **enablement,
            "status": "browsertrix_production_enablement_revocation_reused",
            "idempotent_replay": True,
        }
    if enablement.get("production_enablement_sha256") != _required(
        production_enablement_sha256
    ):
        return blocked("production_enablement_hash_mismatch")
    revoked = _time(revoked_at)
    if revoked is None:
        return blocked("revocation_time_invalid")

    content = {
        "event_type": REVOKE_ACTION,
        "production_enablement_id": enablement_id,
        "production_enablement_sha256": enablement.get(
            "production_enablement_sha256"
        ),
        "revoked_at": revoked.isoformat(),
        "previous_state": enablement.get("enablement_state"),
        "reason": reason,
        "production_enablement_granted": False,
        "production_execution_authorized": False,
        "runtime_execution_performed": False,
        "automatic_retry_performed": False,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "production_enablement_event_id": f"browsertrix-enablement-event-{digest[:24]}",
        "production_enablement_event_sha256": digest,
    }
    result = _record(REVOKE_ACTION, actor, enablement_id, event, ip_address)
    return {
        **result,
        "status": "browsertrix_production_enablement_revoked",
        "idempotent_replay": False,
    }


def validate_runtime_authorization(
    *,
    runtime_authorization: dict[str, Any] | None,
    execution_plan: dict[str, Any] | None,
    deployment_policy: dict[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(runtime_authorization, dict) or runtime_authorization.get(
        "status"
    ) != "browsertrix_production_execution_authorized":
        return blocked("claimed_production_runtime_authorization_required")
    if not isinstance(execution_plan, dict) or not isinstance(deployment_policy, dict):
        return blocked("production_runtime_binding_required")
    authorization = runtime_authorization.get("runtime_authorization") or {}
    if runtime_authorization.get("runtime_authorization_sha256") != _sha(authorization):
        return blocked("runtime_authorization_hash_mismatch")
    checks = {
        "execution_plan_id": authorization.get("production_execution_plan_id")
        == execution_plan.get("execution_plan_id"),
        "execution_plan_sha256": authorization.get(
            "production_execution_plan_sha256"
        )
        == execution_plan.get("execution_plan_sha256"),
        "deployment_id": authorization.get("deployment_id")
        == deployment_policy.get("deployment_id"),
        "runtime": authorization.get("runtime") == deployment_policy.get("runtime"),
        "image_digest": authorization.get("image_digest")
        == deployment_policy.get("image_digest"),
        "network_name": authorization.get("network_name")
        == deployment_policy.get("network_name"),
        "approved_storage_root": authorization.get("approved_storage_root")
        == deployment_policy.get("approved_storage_root"),
        "case_id": authorization.get("case_id")
        == (execution_plan.get("prepared_request") or {}).get("case_id"),
        "approved_domain": authorization.get("approved_domain")
        == execution_plan.get("approved_domain"),
    }
    if not all(checks.values()):
        return blocked("production_runtime_authorization_scope_mismatch", checks=checks)
    requested = _time(deployment_policy.get("execution_requested_at"))
    claimed = _time(authorization.get("claimed_at"))
    expires = _time(authorization.get("expires_at"))
    if requested is None or claimed is None or expires is None:
        return blocked("production_runtime_authorization_times_invalid")
    if not (claimed <= requested < expires):
        return blocked("production_runtime_authorization_expired")
    if authorization.get("single_use") is not True:
        return blocked("single_use_runtime_authorization_required")
    if authorization.get("automatic_execution") is not False or authorization.get(
        "automatic_retry"
    ) is not False:
        return blocked("automatic_production_execution_prohibited")
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "production_runtime_authorization_validated",
        "production_enablement_id": authorization.get("production_enablement_id"),
        "production_enablement_sha256": authorization.get(
            "production_enablement_sha256"
        ),
        "runtime_authorization_sha256": runtime_authorization.get(
            "runtime_authorization_sha256"
        ),
        "production_enablement_granted": True,
        "production_execution_authorized": True,
        "runtime_execution_performed": False,
        "automatic_retry_performed": False,
    }
