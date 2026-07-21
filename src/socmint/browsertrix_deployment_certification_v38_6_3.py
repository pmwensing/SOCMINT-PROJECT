from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable
from urllib.parse import urlsplit, urlunsplit

from .browsertrix_execution_v38_6_1 import (
    ExecutionResult,
    execute_browsertrix_capture,
    validate_controlled_browsertrix_execution,
)

SCHEMA = "socmint.browsertrix_deployment_certification.v38_6_3"
VERSION = "v38.6.3"
CERTIFICATION_ENVIRONMENTS = {"isolated_deployment", "staging"}


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _required(value: Any) -> str:
    return str(value or "").strip()


def _valid_sha256(value: Any) -> bool:
    raw = _required(value).lower()
    return len(raw) == 64 and all(char in "0123456789abcdef" for char in raw)


def _normalize_url(value: Any) -> str | None:
    raw = _required(value)
    if not raw:
        return None
    try:
        parsed = urlsplit(raw)
        port = parsed.port
    except ValueError:
        return None
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return None
    if parsed.username or parsed.password:
        return None
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host:
        return None
    authority = host if port is None else f"{host}:{port}"
    return urlunsplit(
        (parsed.scheme.lower(), authority, parsed.path or "/", parsed.query, "")
    )


def _host(url: str) -> str:
    return (urlsplit(url).hostname or "").lower().rstrip(".")


def blocked(key: str, **details: Any) -> dict[str, Any]:
    result = {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key}],
        "certification_executor_called": False,
        "fixture_request_performed": False,
        "external_probe_performed": False,
        "external_egress_succeeded": False,
        "automatic_retry_performed": False,
        "production_enablement_granted": False,
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


@dataclass(frozen=True)
class DeploymentCertificationObservation:
    certification_plan_id: str
    certification_plan_sha256: str
    runtime_request_id: str
    runtime_sha256: str
    fixture_url: str
    fixture_status: int
    fixture_content_sha256: str
    external_probe_url: str
    external_probe_blocked: bool
    external_probe_response_received: bool
    network_isolated: bool
    egress_policy_enforced: bool
    dns_policy_enforced: bool
    target_binding_enforced: bool
    successful_hosts: list[str]
    attempt_count: int
    automatic_retry_performed: bool
    storage_host_path: str
    storage_approved_root: str
    storage_cleanup_completed: bool
    output_quarantine_required: bool
    execution_result: ExecutionResult


CertificationExecutor = Callable[
    [dict[str, Any]], DeploymentCertificationObservation
]


def prepare_deployment_certification(
    *,
    runtime_request: dict[str, Any] | None,
    actor: str,
    certification_environment: str,
    fixture_url: str,
    fixture_content_sha256: str,
    external_probe_url: str,
    reason: str,
    operator_confirmed: bool,
    standard_ci_live_execution: bool = False,
    production_enablement_requested: bool = False,
) -> dict[str, Any]:
    if not isinstance(runtime_request, dict) or runtime_request.get(
        "status"
    ) != "browsertrix_container_runtime_prepared":
        return blocked("prepared_container_runtime_required")
    if runtime_request.get("runtime_enabled") is not True:
        return blocked("enabled_container_runtime_required")
    if operator_confirmed is not True:
        return blocked("certification_operator_confirmation_required")
    actor = _required(actor)
    reason = _required(reason)
    environment = _required(certification_environment)
    if not actor:
        return blocked("actor_required")
    if not reason:
        return blocked("administrative_reason_required")
    if environment not in CERTIFICATION_ENVIRONMENTS:
        return blocked("deployment_certification_environment_required")
    if standard_ci_live_execution is not False:
        return blocked("standard_ci_live_execution_prohibited")
    if production_enablement_requested is not False:
        return blocked("production_enablement_not_available_in_certification")

    normalized_fixture = _normalize_url(fixture_url)
    normalized_probe = _normalize_url(external_probe_url)
    if normalized_fixture is None or not _host(normalized_fixture).endswith(".test"):
        return blocked("fictional_test_fixture_url_required")
    if normalized_probe is None or not _host(normalized_probe).endswith(".invalid"):
        return blocked("blocked_external_probe_url_required")
    if _host(normalized_fixture) == _host(normalized_probe):
        return blocked("fixture_and_probe_hosts_must_differ")
    if not _valid_sha256(fixture_content_sha256):
        return blocked("fixture_content_sha256_invalid")

    execution_plan = runtime_request.get("execution_plan") or {}
    if execution_plan.get("requested_url") != normalized_fixture:
        return blocked("fixture_execution_plan_binding_mismatch")
    if runtime_request.get("execution_plan_sha256") != execution_plan.get(
        "execution_plan_sha256"
    ):
        return blocked("runtime_execution_plan_hash_mismatch")
    if not _required(runtime_request.get("runtime_request_id")) or not _required(
        runtime_request.get("runtime_sha256")
    ):
        return blocked("runtime_request_identity_required")
    network_controls = runtime_request.get("network_controls") or {}
    required_network_controls = {
        "network_configured",
        "egress_policy_verified",
        "dns_policy_verified",
        "approved_target_binding_verified",
    }
    if not required_network_controls.issubset(network_controls) or not all(
        network_controls.get(key) is True for key in required_network_controls
    ):
        return blocked("verified_network_containment_required")
    storage = runtime_request.get("storage") or {}
    if not _required(storage.get("host_path")) or not _required(
        storage.get("approved_root")
    ):
        return blocked("certification_storage_binding_required")

    plan = {
        "schema": SCHEMA,
        "version": VERSION,
        "deployment_only": True,
        "certification_environment": environment,
        "actor": actor,
        "reason": reason,
        "runtime_request_id": runtime_request["runtime_request_id"],
        "runtime_sha256": runtime_request["runtime_sha256"],
        "execution_plan_id": runtime_request["execution_plan_id"],
        "execution_plan_sha256": runtime_request["execution_plan_sha256"],
        "runtime": runtime_request.get("runtime"),
        "runtime_version": runtime_request.get("runtime_version"),
        "image_reference": runtime_request.get("image_reference"),
        "image_digest": runtime_request.get("image_digest"),
        "network_name": runtime_request.get("network_name"),
        "network_controls": network_controls,
        "storage": storage,
        "fixture_url": normalized_fixture,
        "fixture_host": _host(normalized_fixture),
        "fixture_content_sha256": _required(fixture_content_sha256).lower(),
        "external_probe_url": normalized_probe,
        "external_probe_host": _host(normalized_probe),
        "expected_proofs": {
            "fixture_request_succeeds": True,
            "external_probe_is_blocked": True,
            "dns_policy_is_enforced": True,
            "egress_policy_is_enforced": True,
            "target_binding_is_enforced": True,
            "single_attempt_only": True,
            "storage_cleanup_completes": True,
            "preservation_result_validates": True,
        },
        "standard_ci_live_execution": False,
        "production_enablement_requested": False,
        "max_attempts": 1,
        "automatic_retry": False,
        "runtime_request": runtime_request,
    }
    digest = _sha(plan)
    return {
        **plan,
        "status": "browsertrix_deployment_certification_prepared",
        "certification_plan_id": f"browsertrix-certification-{digest[:24]}",
        "certification_plan_sha256": digest,
        "certification_executor_called": False,
        "production_enablement_granted": False,
    }


def execute_deployment_certification(
    *,
    certification_plan: dict[str, Any] | None,
    executor: CertificationExecutor,
) -> dict[str, Any]:
    if not isinstance(certification_plan, dict) or certification_plan.get(
        "status"
    ) != "browsertrix_deployment_certification_prepared":
        return blocked("prepared_deployment_certification_required")
    if certification_plan.get("standard_ci_live_execution") is not False:
        return blocked("standard_ci_live_execution_prohibited")
    if certification_plan.get("production_enablement_requested") is not False:
        return blocked("production_enablement_not_available_in_certification")
    if certification_plan.get("max_attempts") != 1 or certification_plan.get(
        "automatic_retry"
    ) is not False:
        return blocked("single_certification_attempt_required")

    try:
        observation = executor(certification_plan)
    except Exception as exc:
        return {
            **blocked(
                "deployment_certification_executor_failed",
                error_type=type(exc).__name__,
            ),
            "status": "browsertrix_deployment_certification_failed",
            "certification_executor_called": True,
            "quarantine_required": True,
            "cleanup_required": True,
        }
    if not isinstance(observation, DeploymentCertificationObservation):
        return blocked("deployment_certification_observation_required")

    exact_bindings = {
        "certification_plan_id": observation.certification_plan_id
        == certification_plan.get("certification_plan_id"),
        "certification_plan_sha256": observation.certification_plan_sha256
        == certification_plan.get("certification_plan_sha256"),
        "runtime_request_id": observation.runtime_request_id
        == certification_plan.get("runtime_request_id"),
        "runtime_sha256": observation.runtime_sha256
        == certification_plan.get("runtime_sha256"),
        "fixture_url": _normalize_url(observation.fixture_url)
        == certification_plan.get("fixture_url"),
        "external_probe_url": _normalize_url(observation.external_probe_url)
        == certification_plan.get("external_probe_url"),
    }
    if not all(exact_bindings.values()):
        return {
            **blocked(
                "certification_observation_binding_mismatch",
                exact_bindings=exact_bindings,
            ),
            "certification_executor_called": True,
        }

    if observation.attempt_count != 1 or observation.automatic_retry_performed:
        return {
            **blocked("single_certification_attempt_required"),
            "certification_executor_called": True,
        }
    if observation.fixture_status < 200 or observation.fixture_status >= 300:
        return {
            **blocked("fictional_fixture_request_failed"),
            "certification_executor_called": True,
        }
    if observation.fixture_content_sha256.lower() != certification_plan.get(
        "fixture_content_sha256"
    ):
        return {
            **blocked("fictional_fixture_content_hash_mismatch"),
            "certification_executor_called": True,
        }
    if (
        observation.external_probe_blocked is not True
        or observation.external_probe_response_received is not False
    ):
        return {
            **blocked("external_egress_probe_not_blocked"),
            "certification_executor_called": True,
            "external_probe_performed": True,
            "external_egress_succeeded": observation.external_probe_response_received,
        }

    containment = {
        "network_isolated": observation.network_isolated,
        "egress_policy_enforced": observation.egress_policy_enforced,
        "dns_policy_enforced": observation.dns_policy_enforced,
        "target_binding_enforced": observation.target_binding_enforced,
    }
    if not all(value is True for value in containment.values()):
        return {
            **blocked(
                "deployment_network_containment_not_proven",
                containment=containment,
            ),
            "certification_executor_called": True,
        }
    if sorted(set(observation.successful_hosts)) != [
        certification_plan["fixture_host"]
    ]:
        return {
            **blocked(
                "unexpected_successful_network_host",
                successful_hosts=sorted(set(observation.successful_hosts)),
            ),
            "certification_executor_called": True,
        }

    expected_storage = certification_plan.get("storage") or {}
    storage_proofs = {
        "host_path": observation.storage_host_path
        == _required(expected_storage.get("host_path")),
        "approved_root": observation.storage_approved_root
        == _required(expected_storage.get("approved_root")),
        "cleanup_completed": observation.storage_cleanup_completed is True,
        "quarantine_not_required": observation.output_quarantine_required is False,
    }
    if not all(storage_proofs.values()):
        return {
            **blocked(
                "deployment_storage_certification_failed",
                storage_proofs=storage_proofs,
            ),
            "certification_executor_called": True,
            "cleanup_required": True,
            "quarantine_required": True,
        }

    execution_plan = certification_plan["runtime_request"]["execution_plan"]
    execution_envelope = execute_browsertrix_capture(
        execution_plan=execution_plan,
        executor=lambda _: observation.execution_result,
    )
    validation = validate_controlled_browsertrix_execution(
        execution_plan=execution_plan,
        execution_result=execution_envelope,
    )
    if validation.get("status") != "browsertrix_result_validated":
        return {
            **blocked(
                "certification_preservation_result_invalid",
                validation=validation,
            ),
            "status": "browsertrix_deployment_certification_failed",
            "certification_executor_called": True,
            "fixture_request_performed": True,
            "external_probe_performed": True,
            "quarantine_required": True,
            "cleanup_required": True,
        }

    evidence = {
        "certification_plan_id": certification_plan["certification_plan_id"],
        "certification_plan_sha256": certification_plan[
            "certification_plan_sha256"
        ],
        "runtime_request_id": certification_plan["runtime_request_id"],
        "runtime_sha256": certification_plan["runtime_sha256"],
        "execution_plan_id": certification_plan["execution_plan_id"],
        "execution_plan_sha256": certification_plan["execution_plan_sha256"],
        "fixture_url": certification_plan["fixture_url"],
        "fixture_content_sha256": certification_plan["fixture_content_sha256"],
        "external_probe_url": certification_plan["external_probe_url"],
        "successful_hosts": sorted(set(observation.successful_hosts)),
        "containment": containment,
        "storage_proofs": storage_proofs,
        "preservation_manifest_sha256": validation.get(
            "preservation_manifest_sha256"
        ),
        "execution_result_sha256": execution_envelope.get(
            "execution_result_sha256"
        ),
        "attempt_count": 1,
        "automatic_retry_performed": False,
    }
    certification_sha256 = _sha(evidence)
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "browsertrix_deployment_certification_passed",
        "certification_id": f"browsertrix-certification-result-{certification_sha256[:24]}",
        "certification_sha256": certification_sha256,
        "evidence": evidence,
        "required_proofs": {
            "fictional_fixture_capture": True,
            "fixture_content_hash_match": True,
            "external_egress_blocked": True,
            "dns_policy_enforced": True,
            "egress_policy_enforced": True,
            "approved_target_binding_enforced": True,
            "single_attempt_only": True,
            "storage_cleanup_completed": True,
            "preservation_result_validated": True,
        },
        "certification_executor_called": True,
        "fixture_request_performed": True,
        "external_probe_performed": True,
        "external_egress_succeeded": False,
        "automatic_retry_performed": False,
        "cleanup_required": False,
        "quarantine_required": False,
        "deployment_certification_passed": True,
        "production_enablement_granted": False,
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
        "next_action": (
            "implement_v38_6_4_certification_bound_production_enablement_gate"
        ),
    }
