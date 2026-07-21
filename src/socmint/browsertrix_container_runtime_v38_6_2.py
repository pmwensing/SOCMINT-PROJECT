from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

from .browsertrix_execution_v38_6_1 import ExecutionResult, PINNED_IMAGE
from .browsertrix_production_enablement_v38_6_4 import (
    find_enablement,
    validate_runtime_authorization,
)
from .durable_execution_ledger_v35_1 import create_execution, transition_execution

SCHEMA = "socmint.browsertrix_container_runtime.v38_6_2"
VERSION = "v38.6.4"
SUPPORTED_RUNTIMES = {"docker", "podman"}
EXECUTION_MODES = {"deployment_certification", "production"}
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
MAX_LOG_CHARS = 200_000
PRODUCTION_ACTION = "execute_browsertrix_production_capture"
PRODUCTION_DELEGATE = (
    "browsertrix_container_runtime_v38_6_2.execute_container_runtime"
)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _host(value: Any) -> str:
    try:
        return (urlsplit(str(value or "")).hostname or "").lower().rstrip(".")
    except ValueError:
        return ""


def blocked(key: str, **details: Any) -> dict[str, Any]:
    result = {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key}],
        "runtime_enabled": False,
        "container_started": False,
        "network_request_performed": False,
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


@dataclass(frozen=True)
class ResolvedStorageTarget:
    logical_uri: str
    host_path: str
    approved_root: str
    created_empty: bool
    symlink_safe: bool
    restrictive_permissions: bool


@dataclass(frozen=True)
class RuntimeInspection:
    runtime: str
    binary_path: str
    runtime_version: str
    image_reference: str
    local_image_digest: str
    image_present_locally: bool


@dataclass(frozen=True)
class ProcessOutcome:
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False
    cancelled: bool = False


StorageResolver = Callable[[str], ResolvedStorageTarget]
RuntimeInspector = Callable[[str, str], RuntimeInspection]
ProcessRunner = Callable[[list[str], int], ProcessOutcome]
ResultLoader = Callable[
    [dict[str, Any], ResolvedStorageTarget, ProcessOutcome], ExecutionResult
]


def resolve_private_storage(
    logical_uri: str, approved_root: str
) -> ResolvedStorageTarget:
    if not logical_uri.startswith("private://"):
        raise ValueError("unsupported storage URI")
    relative = logical_uri.removeprefix("private://").strip("/")
    if not relative or any(
        part in {"", ".", ".."} for part in Path(relative).parts
    ):
        raise ValueError("unsafe storage path")
    root = Path(approved_root).expanduser().resolve(strict=True)
    destination = (root / relative).resolve(strict=False)
    if root != destination and root not in destination.parents:
        raise ValueError("storage path escapes approved root")
    blocked_names = {
        ".ssh",
        ".gnupg",
        ".config",
        "credentials",
        "secrets",
        "profiles",
    }
    if blocked_names.intersection(part.lower() for part in destination.parts):
        raise ValueError("sensitive storage path prohibited")
    destination.mkdir(parents=True, exist_ok=False)
    os.chmod(destination, 0o700)
    resolved = destination.resolve(strict=True)
    if root != resolved and root not in resolved.parents:
        raise ValueError("resolved storage path escapes approved root")
    return ResolvedStorageTarget(
        logical_uri=logical_uri,
        host_path=str(resolved),
        approved_root=str(root),
        created_empty=not any(resolved.iterdir()),
        symlink_safe=not resolved.is_symlink(),
        restrictive_permissions=(resolved.stat().st_mode & 0o077) == 0,
    )


def inspect_local_runtime(runtime: str, image_reference: str) -> RuntimeInspection:
    if runtime not in SUPPORTED_RUNTIMES:
        raise ValueError("unsupported runtime")
    version = subprocess.run(
        [runtime, "--version"],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    ).stdout.strip()
    inspect = subprocess.run(
        [
            runtime,
            "image",
            "inspect",
            image_reference,
            "--format",
            "{{json .RepoDigests}}",
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=15,
    )
    repo_digests = json.loads(inspect.stdout or "[]")
    local_digest = ""
    for item in repo_digests:
        if "@sha256:" in item:
            local_digest = item.rsplit("@", 1)[1]
            break
    return RuntimeInspection(
        runtime=runtime,
        binary_path=runtime,
        runtime_version=version,
        image_reference=image_reference,
        local_image_digest=local_digest,
        image_present_locally=bool(local_digest),
    )


def subprocess_runner(command: list[str], timeout_seconds: int) -> ProcessOutcome:
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            shell=False,
            timeout=timeout_seconds,
            check=False,
        )
        return ProcessOutcome(
            exit_code=completed.returncode,
            stdout=(completed.stdout or "")[:MAX_LOG_CHARS],
            stderr=(completed.stderr or "")[:MAX_LOG_CHARS],
        )
    except subprocess.TimeoutExpired as exc:
        return ProcessOutcome(
            exit_code=124,
            stdout=str(exc.stdout or "")[:MAX_LOG_CHARS],
            stderr=str(exc.stderr or "")[:MAX_LOG_CHARS],
            timed_out=True,
        )


def _certification_mode_allowed(
    execution_plan: dict[str, Any],
    deployment_policy: dict[str, Any],
    production_authorization: dict[str, Any] | None,
) -> dict[str, Any]:
    if deployment_policy.get("certification_run") is not True:
        return blocked("explicit_deployment_certification_run_required")
    if production_authorization is not None:
        return blocked("production_authorization_prohibited_in_certification_mode")
    if not _host(execution_plan.get("requested_url")).endswith(".test"):
        return blocked("fictional_test_target_required_for_certification")
    return {
        "status": "deployment_certification_mode_validated",
        "production_authorization": None,
    }


def _production_mode_allowed(
    execution_plan: dict[str, Any],
    deployment_policy: dict[str, Any],
    production_authorization: dict[str, Any] | None,
) -> dict[str, Any]:
    validation = validate_runtime_authorization(
        runtime_authorization=production_authorization,
        execution_plan=execution_plan,
        deployment_policy=deployment_policy,
    )
    if validation.get("status") != "production_runtime_authorization_validated":
        return blocked(
            "certification_bound_production_authorization_required",
            authorization_validation=validation,
        )
    enablement = find_enablement(
        str(validation.get("production_enablement_id") or "")
    )
    if enablement is None or enablement.get("enablement_state") != "claimed":
        return blocked("current_claimed_production_enablement_required")
    claim_event = enablement.get("claim_event") or {}
    if claim_event.get("runtime_authorization_sha256") != validation.get(
        "runtime_authorization_sha256"
    ):
        return blocked("persisted_runtime_authorization_mismatch")
    return {
        "status": "production_mode_validated",
        "production_authorization": {
            "production_enablement_id": validation.get(
                "production_enablement_id"
            ),
            "production_enablement_sha256": validation.get(
                "production_enablement_sha256"
            ),
            "runtime_authorization_sha256": validation.get(
                "runtime_authorization_sha256"
            ),
        },
    }


def prepare_container_runtime(
    *,
    execution_plan: dict[str, Any] | None,
    deployment_policy: dict[str, Any] | None,
    storage_resolver: StorageResolver,
    runtime_inspector: RuntimeInspector,
    production_authorization: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(execution_plan, dict) or execution_plan.get(
        "status"
    ) != "browsertrix_execution_prepared":
        return blocked("prepared_execution_plan_required")
    if not isinstance(deployment_policy, dict):
        return blocked("deployment_runtime_policy_required")
    if deployment_policy.get("runtime_enabled") is not True:
        return blocked("browsertrix_runtime_disabled")
    if deployment_policy.get("operator_confirmed") is not True:
        return blocked("runtime_operator_confirmation_required")
    if deployment_policy.get("execution_plan_sha256") != execution_plan.get(
        "execution_plan_sha256"
    ):
        return blocked("runtime_execution_plan_binding_mismatch")

    execution_mode = str(deployment_policy.get("execution_mode") or "")
    if execution_mode not in EXECUTION_MODES:
        return blocked("explicit_runtime_execution_mode_required")
    if execution_mode == "deployment_certification":
        mode_validation = _certification_mode_allowed(
            execution_plan,
            deployment_policy,
            production_authorization,
        )
    else:
        mode_validation = _production_mode_allowed(
            execution_plan,
            deployment_policy,
            production_authorization,
        )
    if mode_validation.get("status") == "blocked":
        return mode_validation

    runtime = str(deployment_policy.get("runtime") or "")
    if runtime not in SUPPORTED_RUNTIMES:
        return blocked("approved_container_runtime_required")
    digest = str(deployment_policy.get("image_digest") or "")
    if not DIGEST_RE.fullmatch(digest):
        return blocked("pinned_image_digest_required")
    image_reference = f"{PINNED_IMAGE.split(':', 1)[0]}@{digest}"

    network_name = str(deployment_policy.get("network_name") or "").strip()
    network_controls = {
        key: deployment_policy.get(key) is True
        for key in (
            "network_configured",
            "egress_policy_verified",
            "dns_policy_verified",
            "approved_target_binding_verified",
        )
    }
    if not network_name or not all(network_controls.values()):
        return blocked(
            "verified_network_containment_required",
            network_controls=network_controls,
        )

    approved_storage_root = str(
        deployment_policy.get("approved_storage_root") or ""
    ).strip()
    if not approved_storage_root:
        return blocked("approved_storage_root_required")
    logical_uri = (
        execution_plan.get("container", {}).get("mounts", [{}])[0].get(
            "source", ""
        )
    )
    try:
        storage = storage_resolver(logical_uri)
    except Exception as exc:
        return blocked(
            "private_storage_resolution_failed",
            error_type=type(exc).__name__,
        )
    if not all(
        (
            storage.created_empty,
            storage.symlink_safe,
            storage.restrictive_permissions,
        )
    ):
        return blocked("private_storage_controls_failed")
    if storage.approved_root != approved_storage_root:
        return blocked("approved_storage_root_mismatch")

    try:
        inspection = runtime_inspector(runtime, image_reference)
    except Exception as exc:
        return blocked(
            "container_runtime_inspection_failed",
            error_type=type(exc).__name__,
        )
    if not inspection.image_present_locally:
        return blocked("pinned_image_not_present_locally")
    if (
        inspection.local_image_digest != digest
        or inspection.image_reference != image_reference
    ):
        return blocked("local_image_digest_mismatch")

    container = execution_plan["container"]
    timeout_seconds = (
        int(
            execution_plan["prepared_request"]["resource_limits"][
                "max_duration_seconds"
            ]
        )
        + 30
    )
    command = [
        inspection.binary_path,
        "run",
        "--rm",
        "--read-only",
        "--security-opt",
        "no-new-privileges",
        "--cap-drop",
        "ALL",
        "--pids-limit",
        str(container["process_limit"]),
        "--cpus",
        str(container["cpu_limit"]),
        "--memory",
        f"{container['memory_limit_mb']}m",
        "--network",
        network_name,
        "--mount",
        f"type=bind,source={storage.host_path},target=/crawls",
        "--env",
        "TZ=UTC",
        "--env",
        "BROWSERTRIX_DISABLE_TELEMETRY=1",
        image_reference,
        execution_plan["executable"],
        *execution_plan["arguments"],
    ]
    envelope = {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "browsertrix_container_runtime_prepared",
        "execution_mode": execution_mode,
        "execution_plan_id": execution_plan["execution_plan_id"],
        "execution_plan_sha256": execution_plan["execution_plan_sha256"],
        "runtime": runtime,
        "runtime_version": inspection.runtime_version,
        "runtime_binary": inspection.binary_path,
        "image_reference": image_reference,
        "image_digest": digest,
        "image_pull_allowed": False,
        "network_name": network_name,
        "network_controls": network_controls,
        "storage": {
            "logical_uri": storage.logical_uri,
            "host_path": storage.host_path,
            "approved_root": storage.approved_root,
        },
        "command": command,
        "shell": False,
        "timeout_seconds": timeout_seconds,
        "max_attempts": 1,
        "automatic_retry": False,
        "actor": str(deployment_policy.get("actor") or "").strip(),
        "deployment_policy": {
            key: deployment_policy.get(key)
            for key in (
                "execution_mode",
                "deployment_id",
                "execution_requested_at",
                "runtime",
                "image_digest",
                "network_name",
                "approved_storage_root",
            )
        },
        "production_authorization": mode_validation.get(
            "production_authorization"
        ),
        "execution_plan": execution_plan,
    }
    if execution_mode == "production" and not envelope["actor"]:
        return blocked("production_runtime_actor_required")
    runtime_sha256 = _sha(envelope)
    return {
        **envelope,
        "runtime_request_id": f"browsertrix-runtime-{runtime_sha256[:24]}",
        "runtime_sha256": runtime_sha256,
        "runtime_enabled": True,
        "container_started": False,
        "network_request_performed": False,
    }


def _begin_production_execution(
    runtime_request: dict[str, Any],
) -> dict[str, Any]:
    authorization = runtime_request.get("production_authorization") or {}
    execution_plan = runtime_request.get("execution_plan") or {}
    prepared_request = execution_plan.get("prepared_request") or {}
    execution = create_execution(
        confirmation_sha256=str(
            authorization.get("runtime_authorization_sha256") or ""
        ),
        actor=str(runtime_request.get("actor") or ""),
        case_id=str(prepared_request.get("case_id") or ""),
        governance_action=PRODUCTION_ACTION,
        delegate_service=PRODUCTION_DELEGATE,
    )
    if not execution.get("created"):
        return blocked(
            "production_runtime_authorization_already_consumed",
            execution_id=execution.get("execution_id"),
            execution_state=execution.get("state"),
        )
    running = transition_execution(
        execution_id=execution["execution_id"],
        expected_state="pending",
        expected_version=execution["state_version"],
        new_state="running",
        actor=str(runtime_request.get("actor") or ""),
        reason="certification_bound_browsertrix_execution_started",
        metadata={
            "runtime_request_id": runtime_request.get("runtime_request_id"),
            "runtime_sha256": runtime_request.get("runtime_sha256"),
            "production_enablement_id": authorization.get(
                "production_enablement_id"
            ),
        },
    )
    return {
        "status": "production_execution_started",
        "execution": execution,
        "running": running,
    }


def _finish_production_execution(
    runtime_request: dict[str, Any],
    started: dict[str, Any],
    state: str,
    reason: str,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    running = started["running"]
    return transition_execution(
        execution_id=running["execution_id"],
        expected_state="running",
        expected_version=running["state_version"],
        new_state=state,
        actor=str(runtime_request.get("actor") or ""),
        reason=reason,
        metadata=metadata,
    )


def execute_container_runtime(
    *,
    runtime_request: dict[str, Any] | None,
    process_runner: ProcessRunner,
    result_loader: ResultLoader,
) -> dict[str, Any]:
    if not isinstance(runtime_request, dict) or runtime_request.get(
        "status"
    ) != "browsertrix_container_runtime_prepared":
        return blocked("prepared_container_runtime_required")
    if (
        runtime_request.get("shell") is not False
        or runtime_request.get("automatic_retry") is not False
    ):
        return blocked("unsafe_runtime_execution_prohibited")
    if runtime_request.get("max_attempts") != 1:
        return blocked("single_runtime_attempt_required")

    started: dict[str, Any] | None = None
    if runtime_request.get("execution_mode") == "production":
        started = _begin_production_execution(runtime_request)
        if started.get("status") == "blocked":
            return started

    try:
        outcome = process_runner(
            runtime_request["command"], runtime_request["timeout_seconds"]
        )
    except Exception as exc:
        if started is not None:
            uncertain = _finish_production_execution(
                runtime_request,
                started,
                "uncertain",
                "browsertrix_process_runner_outcome_unknown",
                {"exception_type": type(exc).__name__},
            )
            execution_details = {
                "execution_id": uncertain.get("execution_id"),
                "execution_state": uncertain.get("state"),
            }
        else:
            execution_details = {}
        return {
            **blocked(
                "browsertrix_process_runner_failed",
                error_type=type(exc).__name__,
            ),
            "status": "browsertrix_container_execution_uncertain",
            "container_started": True,
            "network_request_performed": False,
            "cleanup_required": True,
            "quarantine_required": True,
            "external_effect_unknown": True,
            **execution_details,
        }

    storage_data = runtime_request["storage"]
    storage = ResolvedStorageTarget(
        logical_uri=storage_data["logical_uri"],
        host_path=storage_data["host_path"],
        approved_root=storage_data["approved_root"],
        created_empty=True,
        symlink_safe=True,
        restrictive_permissions=True,
    )
    if outcome.exit_code != 0 or outcome.timed_out or outcome.cancelled:
        execution_details: dict[str, Any] = {}
        if started is not None:
            failed = _finish_production_execution(
                runtime_request,
                started,
                "failed",
                "browsertrix_container_execution_failed",
                {
                    "exit_code": outcome.exit_code,
                    "timed_out": outcome.timed_out,
                    "cancelled": outcome.cancelled,
                },
            )
            execution_details = {
                "execution_id": failed.get("execution_id"),
                "execution_state": failed.get("state"),
            }
        return {
            **blocked(
                "browsertrix_container_execution_failed",
                exit_code=outcome.exit_code,
                timed_out=outcome.timed_out,
                cancelled=outcome.cancelled,
                stderr=outcome.stderr,
            ),
            "status": "browsertrix_container_execution_failed",
            "runtime_request_id": runtime_request["runtime_request_id"],
            "runtime_sha256": runtime_request["runtime_sha256"],
            "container_started": True,
            "network_request_performed": True,
            "cleanup_required": True,
            "quarantine_required": True,
            **execution_details,
        }

    try:
        result = result_loader(runtime_request["execution_plan"], storage, outcome)
    except Exception as exc:
        execution_details = {}
        if started is not None:
            uncertain = _finish_production_execution(
                runtime_request,
                started,
                "uncertain",
                "browsertrix_result_loader_failed_after_external_effect",
                {"exception_type": type(exc).__name__},
            )
            execution_details = {
                "execution_id": uncertain.get("execution_id"),
                "execution_state": uncertain.get("state"),
            }
        return {
            **blocked(
                "browsertrix_result_loader_failed",
                error_type=type(exc).__name__,
            ),
            "status": "browsertrix_container_execution_uncertain",
            "runtime_request_id": runtime_request["runtime_request_id"],
            "runtime_sha256": runtime_request["runtime_sha256"],
            "container_started": True,
            "network_request_performed": True,
            "cleanup_required": True,
            "quarantine_required": True,
            "external_effect_unknown": True,
            **execution_details,
        }

    execution_details = {}
    if started is not None:
        succeeded = _finish_production_execution(
            runtime_request,
            started,
            "succeeded",
            "browsertrix_container_execution_completed",
            {
                "runtime_request_id": runtime_request.get("runtime_request_id"),
                "runtime_sha256": runtime_request.get("runtime_sha256"),
                "result_summary_sha256": _sha(
                    {
                        "exit_code": result.exit_code,
                        "final_url": result.final_url,
                        "page_count": result.page_count,
                        "downloaded_bytes": result.downloaded_bytes,
                        "outputs": result.outputs,
                    }
                ),
            },
        )
        execution_details = {
            "execution_id": succeeded.get("execution_id"),
            "execution_state": succeeded.get("state"),
            "durable_replay_protection": True,
        }
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "browsertrix_container_execution_completed",
        "runtime_request_id": runtime_request["runtime_request_id"],
        "runtime_sha256": runtime_request["runtime_sha256"],
        "execution_mode": runtime_request.get("execution_mode"),
        "execution_plan_id": runtime_request["execution_plan_id"],
        "execution_plan_sha256": runtime_request["execution_plan_sha256"],
        "attempt_count": 1,
        "container_started": True,
        "network_request_performed": True,
        "automatic_retry_performed": False,
        "cleanup_required": True,
        "quarantine_required": False,
        "stdout": outcome.stdout,
        "stderr": outcome.stderr,
        "execution_result": result,
        **execution_details,
    }
