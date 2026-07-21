from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable

from .browsertrix_preservation_v38_6 import validate_browsertrix_result

SCHEMA = "socmint.browsertrix_execution.v38_6_1"
VERSION = "v38.6.1"
PINNED_IMAGE = "webrecorder/browsertrix-crawler:1.5.0"
EXECUTABLE = "crawl"


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _required(value: Any) -> str:
    return str(value or "").strip()


def blocked(key: str, **details: Any) -> dict[str, Any]:
    result = {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key}],
        "browsertrix_process_started": False,
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
class ExecutionResult:
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool
    cancelled: bool
    started_at: str
    completed_at: str
    browsertrix_version: str
    browser_version: str
    final_url: str
    redirect_chain: list[dict[str, Any]]
    page_count: int
    downloaded_bytes: int
    outputs: list[dict[str, Any]]


Executor = Callable[[dict[str, Any]], ExecutionResult]


def prepare_browsertrix_execution(
    *,
    prepared_request: dict[str, Any] | None,
    image: str = PINNED_IMAGE,
    cpu_limit: float = 1.0,
    memory_limit_mb: int = 1024,
    process_limit: int = 128,
) -> dict[str, Any]:
    if not isinstance(prepared_request, dict):
        return blocked("prepared_browsertrix_request_required")
    if prepared_request.get("status") != "browsertrix_request_prepared":
        return blocked("prepared_browsertrix_request_required")
    if _required(image) != PINNED_IMAGE:
        return blocked("pinned_browsertrix_image_required")
    if not prepared_request.get("request_sha256") or not prepared_request.get("browser_capture_request_id"):
        return blocked("browser_request_identity_required")

    policy = prepared_request.get("browser_policy") or {}
    required_disabled = {
        "authentication_enabled",
        "credentials_enabled",
        "cookies_supplied",
        "saved_profile_enabled",
        "form_submission_enabled",
        "file_upload_enabled",
        "captcha_bypass_enabled",
        "automatic_retry_enabled",
        "off_domain_navigation_enabled",
    }
    if any(policy.get(key) is not False for key in required_disabled):
        return blocked("unsafe_browser_policy_prohibited")

    try:
        cpu_limit = float(cpu_limit)
        memory_limit_mb = int(memory_limit_mb)
        process_limit = int(process_limit)
    except (TypeError, ValueError):
        return blocked("execution_resource_limits_invalid")
    if cpu_limit <= 0 or cpu_limit > 2 or memory_limit_mb < 256 or memory_limit_mb > 4096 or process_limit < 32 or process_limit > 256:
        return blocked("execution_resource_limits_invalid")

    storage_target = _required(prepared_request.get("storage_target"))
    if not storage_target.startswith("private://"):
        return blocked("approved_private_storage_target_required")

    limits = prepared_request.get("resource_limits") or {}
    required_limits = {
        "max_pages",
        "max_depth",
        "max_duration_seconds",
        "max_download_bytes",
        "max_redirects",
        "navigation_timeout_seconds",
        "max_screenshots",
        "concurrency",
    }
    if not required_limits.issubset(limits):
        return blocked("browser_resource_limits_required")

    output_name = prepared_request["browser_capture_request_id"]
    command = [
        EXECUTABLE,
        "--url",
        prepared_request["requested_url"],
        "--collection",
        output_name,
        "--scopeType",
        "prefix",
        "--maxPageLimit",
        str(limits["max_pages"]),
        "--depth",
        str(limits["max_depth"]),
        "--timeLimit",
        str(limits["max_duration_seconds"]),
        "--sizeLimit",
        str(limits["max_download_bytes"]),
        "--pageLoadTimeout",
        str(limits["navigation_timeout_seconds"]),
        "--workers",
        "1",
        "--generateWACZ",
        "--screenshot",
        "view",
    ]

    plan = {
        "schema": SCHEMA,
        "version": VERSION,
        "browser_capture_request_id": prepared_request["browser_capture_request_id"],
        "request_sha256": prepared_request["request_sha256"],
        "execution_id": prepared_request["execution_id"],
        "requested_url": prepared_request["requested_url"],
        "approved_domain": prepared_request["approved_domain"],
        "image": PINNED_IMAGE,
        "executable": EXECUTABLE,
        "arguments": command[1:],
        "environment": {
            "TZ": "UTC",
            "BROWSERTRIX_DISABLE_TELEMETRY": "1",
        },
        "container": {
            "privileged": False,
            "host_network": False,
            "read_only_root": True,
            "shell": False,
            "automatic_remove": True,
            "cpu_limit": cpu_limit,
            "memory_limit_mb": memory_limit_mb,
            "process_limit": process_limit,
            "mounts": [
                {
                    "source": storage_target,
                    "target": "/crawls",
                    "mode": "rw",
                    "purpose": "capture-output-only",
                }
            ],
        },
        "retry_policy": {"automatic_retry": False, "max_attempts": 1},
        "cleanup_policy": {
            "cleanup_on_success": True,
            "cleanup_on_failure": True,
            "cleanup_on_timeout": True,
            "cleanup_on_cancel": True,
        },
        "prepared_request": prepared_request,
    }
    plan_sha256 = _sha(plan)
    return {
        **plan,
        "status": "browsertrix_execution_prepared",
        "execution_plan_id": f"browsertrix-execution-{plan_sha256[:24]}",
        "execution_plan_sha256": plan_sha256,
        "browsertrix_process_started": False,
        "network_request_performed": False,
        "automatic_retry_performed": False,
    }


def execute_browsertrix_capture(*, execution_plan: dict[str, Any] | None, executor: Executor) -> dict[str, Any]:
    if not isinstance(execution_plan, dict) or execution_plan.get("status") != "browsertrix_execution_prepared":
        return blocked("prepared_execution_plan_required")
    if execution_plan.get("image") != PINNED_IMAGE or execution_plan.get("executable") != EXECUTABLE:
        return blocked("execution_plan_runtime_identity_mismatch")
    if execution_plan.get("container", {}).get("shell") is not False:
        return blocked("shell_execution_prohibited")
    if execution_plan.get("retry_policy") != {"automatic_retry": False, "max_attempts": 1}:
        return blocked("automatic_retry_prohibited")

    try:
        raw = executor(execution_plan)
    except Exception as exc:  # executor boundary must become an explicit failed record
        return {
            **blocked("browsertrix_executor_failed", error_type=type(exc).__name__),
            "status": "browsertrix_execution_failed",
            "browsertrix_process_started": True,
            "network_request_performed": False,
        }

    result = {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "browsertrix_execution_completed" if raw.exit_code == 0 and not raw.timed_out and not raw.cancelled else "browsertrix_execution_failed",
        "execution_plan_id": execution_plan["execution_plan_id"],
        "execution_plan_sha256": execution_plan["execution_plan_sha256"],
        "browser_capture_request_id": execution_plan["browser_capture_request_id"],
        "request_sha256": execution_plan["request_sha256"],
        "execution_id": execution_plan["execution_id"],
        "requested_url": execution_plan["requested_url"],
        "exit_code": int(raw.exit_code),
        "stdout": str(raw.stdout),
        "stderr": str(raw.stderr),
        "timed_out": bool(raw.timed_out),
        "cancelled": bool(raw.cancelled),
        "started_at": raw.started_at,
        "completed_at": raw.completed_at,
        "browsertrix_version": raw.browsertrix_version,
        "browser_version": raw.browser_version,
        "final_url": raw.final_url,
        "redirect_chain": raw.redirect_chain,
        "page_count": int(raw.page_count),
        "downloaded_bytes": int(raw.downloaded_bytes),
        "outputs": raw.outputs,
        "attempt_count": 1,
        "browsertrix_process_started": True,
        "network_request_performed": True,
        "automatic_retry_performed": False,
        "cleanup_required": True,
    }
    return {**result, "execution_result_sha256": _sha(result)}


def validate_controlled_browsertrix_execution(
    *, execution_plan: dict[str, Any] | None, execution_result: dict[str, Any] | None
) -> dict[str, Any]:
    if not isinstance(execution_plan, dict) or execution_plan.get("status") != "browsertrix_execution_prepared":
        return blocked("prepared_execution_plan_required")
    if not isinstance(execution_result, dict):
        return blocked("browsertrix_execution_result_required")
    if execution_result.get("execution_plan_id") != execution_plan.get("execution_plan_id"):
        return blocked("execution_plan_result_binding_mismatch")
    if execution_result.get("execution_plan_sha256") != execution_plan.get("execution_plan_sha256"):
        return blocked("execution_plan_hash_mismatch")
    if execution_result.get("attempt_count") != 1 or execution_result.get("automatic_retry_performed") is not False:
        return blocked("automatic_retry_prohibited")
    if execution_result.get("status") != "browsertrix_execution_completed" or execution_result.get("exit_code") != 0:
        return blocked("successful_browsertrix_execution_required")

    prepared_request = execution_plan["prepared_request"]
    return validate_browsertrix_result(
        prepared_request=prepared_request,
        browser_capture_request_id=execution_result["browser_capture_request_id"],
        request_sha256=execution_result["request_sha256"],
        execution_id=execution_result["execution_id"],
        requested_url=execution_result["requested_url"],
        final_url=execution_result["final_url"],
        redirect_chain=execution_result["redirect_chain"],
        started_at=execution_result["started_at"],
        completed_at=execution_result["completed_at"],
        browsertrix_version=execution_result["browsertrix_version"],
        browser_version=execution_result["browser_version"],
        page_count=execution_result["page_count"],
        downloaded_bytes=execution_result["downloaded_bytes"],
        outputs=execution_result["outputs"],
        completion_status="completed",
    )
