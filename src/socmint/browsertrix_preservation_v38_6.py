from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import PurePath
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from .public_discovery_policy_gate_v38_2 import find_gate_decision
from .public_discovery_request_v38_1 import find_discovery_request

SCHEMA = "socmint.browsertrix_preservation.v38_6"
VERSION = "v38.6.0"
OUTPUT_PROFILE_VERSION = "v38.6.3"
REQUIRED_OUTPUT_ROLES = {"wacz", "crawl_metadata"}
SCREENSHOT_OUTPUT_ROLES = {"screenshot", "screenshot_archive"}
ROLE_MEDIA_TYPES = {
    "wacz": {"application/wacz", "application/octet-stream"},
    "screenshot": {"image/png", "image/jpeg"},
    "screenshot_archive": {
        "application/warc",
        "application/gzip",
        "application/x-gzip",
        "application/octet-stream",
    },
    "crawl_metadata": {
        "application/json",
        "application/jsonl",
        "application/ndjson",
        "application/x-ndjson",
    },
    "warc": {
        "application/warc",
        "application/gzip",
        "application/x-gzip",
        "application/octet-stream",
    },
}


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _required(value: Any) -> str:
    return str(value or "").strip()


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


def _time(value: Any) -> str | None:
    raw = _required(value)
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc).isoformat()


def _host(url: str) -> str:
    return (urlsplit(url).hostname or "").lower().rstrip(".")


def blocked(key: str, **details: Any) -> dict[str, Any]:
    result = {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key}],
        "browsertrix_process_started": False,
        "network_request_performed": False,
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


def _limits(value: Any) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(value, dict):
        return None, "browser_resource_limits_required"
    try:
        limits = {
            "max_pages": int(value.get("max_pages")),
            "max_depth": int(value.get("max_depth")),
            "max_duration_seconds": int(value.get("max_duration_seconds")),
            "max_download_bytes": int(value.get("max_download_bytes")),
            "max_redirects": int(value.get("max_redirects")),
            "navigation_timeout_seconds": int(
                value.get("navigation_timeout_seconds")
            ),
            "max_screenshots": int(value.get("max_screenshots")),
            "concurrency": int(value.get("concurrency", 1)),
        }
    except (TypeError, ValueError):
        return None, "browser_resource_limits_invalid"
    if min(limits.values()) < 0 or limits["max_pages"] < 1:
        return None, "browser_resource_limits_invalid"
    if limits["concurrency"] != 1:
        return None, "single_concurrency_required"
    if limits["max_pages"] > 25 or limits["max_depth"] > 2:
        return None, "browser_scope_limits_exceeded"
    return limits, None


def prepare_browsertrix_request(
    *,
    actor: str,
    discovery_request_id: str,
    gate_decision_id: str,
    public_http_capture: dict[str, Any] | None,
    requested_url: str,
    javascript_justification: str,
    operator_reason: str,
    execution_id: str,
    storage_target: str,
    resource_limits: dict[str, Any] | None,
    allowed_content_types: list[str] | None,
    confirmed: bool,
) -> dict[str, Any]:
    actor = _required(actor)
    discovery_request_id = _required(discovery_request_id)
    gate_decision_id = _required(gate_decision_id)
    javascript_justification = _required(javascript_justification)
    operator_reason = _required(operator_reason)
    execution_id = _required(execution_id)
    storage_target = _required(storage_target)
    normalized_url = _normalize_url(requested_url)

    if confirmed is not True:
        return blocked("explicit_operator_confirmation_required")
    if not actor:
        return blocked("actor_required")
    if not discovery_request_id or not gate_decision_id or not execution_id:
        return blocked("request_gate_execution_binding_required")
    if not javascript_justification:
        return blocked("javascript_capture_justification_required")
    if not operator_reason:
        return blocked("administrative_reason_required")
    if not storage_target.startswith("private://"):
        return blocked("approved_private_storage_target_required")
    if normalized_url is None:
        return blocked("requested_url_invalid")

    request = find_discovery_request(discovery_request_id)
    gate = find_gate_decision(gate_decision_id)
    if request is None:
        return blocked("discovery_request_required")
    if gate is None or gate.get("discovery_request_id") != discovery_request_id:
        return blocked("gate_request_binding_mismatch")
    if gate.get("decision") != "allow" or gate.get("live_network_eligible") is not True:
        return blocked("allowing_live_network_gate_required")
    if gate.get("robots_allowed") is False:
        return blocked("robots_policy_blocks_execution")
    if gate.get("terms_allowed") is False:
        return blocked("terms_policy_blocks_execution")

    if not isinstance(public_http_capture, dict):
        return blocked("v38_5_public_http_preflight_required")
    if public_http_capture.get("status") != "public_http_capture_completed":
        return blocked("successful_v38_5_public_http_preflight_required")
    if public_http_capture.get("discovery_request_id") != discovery_request_id:
        return blocked("v38_5_request_binding_mismatch")
    if public_http_capture.get("gate_decision_id") != gate_decision_id:
        return blocked("v38_5_gate_binding_mismatch")
    if public_http_capture.get("requested_url") != normalized_url:
        return blocked("v38_5_url_binding_mismatch")
    if public_http_capture.get("capture_sha256") is None:
        return blocked("v38_5_capture_hash_required")

    manifest = request.get("manifest") or {}
    approved_domains = {
        str(item).lower().rstrip(".")
        for item in (
            gate.get("approved_domains") or manifest.get("approved_domains") or []
        )
        if _required(item)
    }
    if _host(normalized_url) not in approved_domains:
        return blocked("requested_domain_not_approved")

    limits, limit_error = _limits(resource_limits)
    if limit_error:
        return blocked(limit_error)
    assert limits is not None
    allowed_types = sorted(
        {
            _required(item).lower()
            for item in (allowed_content_types or [])
            if _required(item)
        }
    )
    permitted_types = {"text/html", "application/pdf", "image/png", "image/jpeg"}
    if not allowed_types or any(item not in permitted_types for item in allowed_types):
        return blocked("allowed_content_types_invalid")

    envelope = {
        "schema": SCHEMA,
        "version": VERSION,
        "discovery_request_id": discovery_request_id,
        "gate_decision_id": gate_decision_id,
        "collection_job_binding": manifest.get("collection_job_binding"),
        "case_id": manifest.get("case_id"),
        "purpose": manifest.get("purpose"),
        "execution_id": execution_id,
        "requested_url": normalized_url,
        "approved_domain": _host(normalized_url),
        "javascript_justification": javascript_justification,
        "operator_reason": operator_reason,
        "actor": actor,
        "storage_target": storage_target,
        "resource_limits": limits,
        "allowed_content_types": allowed_types,
        "v38_5_preflight": {
            "capture_sha256": public_http_capture["capture_sha256"],
            "final_url": public_http_capture.get("final_url"),
            "content_sha256": public_http_capture.get("content_sha256"),
        },
        "browser_policy": {
            "authentication_enabled": False,
            "credentials_enabled": False,
            "cookies_supplied": False,
            "saved_profile_enabled": False,
            "form_submission_enabled": False,
            "file_upload_enabled": False,
            "captcha_bypass_enabled": False,
            "automatic_retry_enabled": False,
            "off_domain_navigation_enabled": False,
        },
        "adapter": {"name": "browsertrix-preservation", "version": VERSION},
    }
    request_sha256 = _sha(envelope)
    return {
        **envelope,
        "status": "browsertrix_request_prepared",
        "browser_capture_request_id": f"browsertrix-request-{request_sha256[:24]}",
        "request_sha256": request_sha256,
        "browsertrix_process_started": False,
        "network_request_performed": False,
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


def _outputs(value: Any) -> tuple[list[dict[str, Any]] | None, str | None]:
    if not isinstance(value, list) or not value:
        return None, "preservation_outputs_required"
    normalized: list[dict[str, Any]] = []
    roles: set[str] = set()
    for item in value:
        if not isinstance(item, dict):
            return None, "preservation_output_invalid"
        role = _required(item.get("role"))
        filename = _required(item.get("filename"))
        media_type = _required(item.get("media_type")).lower()
        digest = _required(item.get("sha256")).lower()
        try:
            byte_size = int(item.get("byte_size"))
        except (TypeError, ValueError):
            return None, "preservation_output_invalid"
        if role not in ROLE_MEDIA_TYPES or role in roles:
            return None, "preservation_output_role_invalid"
        if PurePath(filename).name != filename or not filename:
            return None, "preservation_output_filename_invalid"
        if media_type not in ROLE_MEDIA_TYPES[role]:
            return None, "preservation_output_media_type_invalid"
        if len(digest) != 64 or any(
            char not in "0123456789abcdef" for char in digest
        ):
            return None, "preservation_output_hash_invalid"
        if byte_size <= 0:
            return None, "preservation_output_size_invalid"
        normalized.append(
            {
                "role": role,
                "filename": filename,
                "media_type": media_type,
                "sha256": digest,
                "byte_size": byte_size,
            }
        )
        roles.add(role)
    if not REQUIRED_OUTPUT_ROLES.issubset(roles):
        return None, "required_preservation_outputs_missing"
    if not SCREENSHOT_OUTPUT_ROLES.intersection(roles):
        return None, "required_preservation_outputs_missing"
    return sorted(normalized, key=lambda item: item["role"]), None


def validate_browsertrix_result(
    *,
    prepared_request: dict[str, Any] | None,
    browser_capture_request_id: str,
    request_sha256: str,
    execution_id: str,
    requested_url: str,
    final_url: str,
    redirect_chain: list[dict[str, Any]] | None,
    started_at: str,
    completed_at: str,
    browsertrix_version: str,
    browser_version: str,
    page_count: int,
    downloaded_bytes: int,
    outputs: list[dict[str, Any]] | None,
    completion_status: str,
) -> dict[str, Any]:
    if not isinstance(prepared_request, dict) or prepared_request.get(
        "status"
    ) != "browsertrix_request_prepared":
        return blocked("prepared_browsertrix_request_required")
    if prepared_request.get("browser_capture_request_id") != _required(
        browser_capture_request_id
    ):
        return blocked("browser_capture_request_binding_mismatch")
    if prepared_request.get("request_sha256") != _required(request_sha256):
        return blocked("browser_request_hash_mismatch")
    if prepared_request.get("execution_id") != _required(execution_id):
        return blocked("browser_execution_binding_mismatch")
    normalized_requested = _normalize_url(requested_url)
    normalized_final = _normalize_url(final_url)
    if (
        normalized_requested != prepared_request.get("requested_url")
        or normalized_final is None
    ):
        return blocked("browser_result_url_binding_mismatch")
    if _host(normalized_final) != prepared_request.get("approved_domain"):
        return blocked("off_domain_browser_result_blocked")
    if completion_status != "completed":
        return blocked(
            "completed_browsertrix_result_required",
            completion_status=completion_status,
        )

    start = _time(started_at)
    end = _time(completed_at)
    if start is None or end is None or end < start:
        return blocked("browser_capture_times_invalid")
    if not _required(browsertrix_version) or not _required(browser_version):
        return blocked("browser_adapter_versions_required")

    limits = prepared_request["resource_limits"]
    try:
        page_count = int(page_count)
        downloaded_bytes = int(downloaded_bytes)
    except (TypeError, ValueError):
        return blocked("browser_result_metrics_invalid")
    if page_count < 1 or page_count > limits["max_pages"]:
        return blocked("browser_page_limit_exceeded")
    if downloaded_bytes < 1 or downloaded_bytes > limits["max_download_bytes"]:
        return blocked("browser_download_limit_exceeded")
    if not isinstance(redirect_chain, list) or len(redirect_chain) > limits[
        "max_redirects"
    ]:
        return blocked("browser_redirect_limit_exceeded")
    for item in redirect_chain:
        if not isinstance(item, dict):
            return blocked("browser_redirect_chain_invalid")
        from_url = _normalize_url(item.get("from_url"))
        to_url = _normalize_url(item.get("to_url"))
        if (
            from_url is None
            or to_url is None
            or _host(from_url) != prepared_request["approved_domain"]
            or _host(to_url) != prepared_request["approved_domain"]
        ):
            return blocked("off_domain_browser_redirect_blocked")

    normalized_outputs, output_error = _outputs(outputs)
    if output_error:
        return blocked(output_error)
    assert normalized_outputs is not None

    manifest = {
        "schema": SCHEMA,
        "version": VERSION,
        "output_profile_version": OUTPUT_PROFILE_VERSION,
        "browser_capture_request_id": browser_capture_request_id,
        "request_sha256": request_sha256,
        "execution_id": execution_id,
        "requested_url": normalized_requested,
        "final_url": normalized_final,
        "redirect_chain": redirect_chain,
        "started_at": start,
        "completed_at": end,
        "browsertrix_version": _required(browsertrix_version),
        "browser_version": _required(browser_version),
        "page_count": page_count,
        "downloaded_bytes": downloaded_bytes,
        "outputs": normalized_outputs,
    }
    manifest_sha256 = _sha(manifest)
    return {
        **manifest,
        "status": "browsertrix_result_validated",
        "preservation_manifest_sha256": manifest_sha256,
        "browsertrix_process_started": True,
        "network_request_performed": True,
        "raw_content_recorded": False,
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
