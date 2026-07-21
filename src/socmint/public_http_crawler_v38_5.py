from __future__ import annotations

import hashlib
import ipaddress
import json
import socket
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable
from urllib.parse import urljoin, urlsplit, urlunsplit

from .public_discovery_policy_gate_v38_2 import find_gate_decision
from .public_discovery_request_v38_1 import find_discovery_request

SCHEMA = "socmint.public_http_crawler.v38_5"
VERSION = "v38.5.0"
SENSITIVE_HEADERS = {"authorization", "cookie", "proxy-authorization", "set-cookie"}
REDIRECT_CODES = {301, 302, 303, 307, 308}
DEFAULT_ALLOWED_CONTENT_TYPES = (
    "text/html",
    "text/plain",
    "application/pdf",
    "application/json",
    "application/xml",
    "text/xml",
)


@dataclass(frozen=True)
class TransportResponse:
    status_code: int
    url: str
    headers: dict[str, str]
    body: bytes
    elapsed_ms: int = 0


Transport = Callable[[str, dict[str, str], float], TransportResponse]
Resolver = Callable[[str], Iterable[str]]
Sleeper = Callable[[float], None]


def blocked(key: str, **details: Any) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key}],
        "network_request_performed": False,
        "crawler_execution_performed": False,
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
    return urlunsplit((parsed.scheme.lower(), authority, parsed.path or "/", parsed.query, ""))


def _host(url: str) -> str:
    return (urlsplit(url).hostname or "").lower().rstrip(".")


def _normalize_headers(headers: Any) -> tuple[dict[str, str] | None, str | None]:
    if not isinstance(headers, dict):
        return None, "response_headers_object_required"
    normalized: dict[str, str] = {}
    for raw_key, raw_value in headers.items():
        key = _required(raw_key).lower()
        if not key:
            return None, "response_header_invalid"
        if key in SENSITIVE_HEADERS:
            continue
        normalized[key] = _required(raw_value)
    return dict(sorted(normalized.items())), None


def _content_type(headers: dict[str, str]) -> str:
    return headers.get("content-type", "").split(";", 1)[0].strip().lower()


def _default_resolver(host: str) -> Iterable[str]:
    return sorted({item[4][0] for item in socket.getaddrinfo(host, None)})


def _public_ip(address: str) -> bool:
    try:
        parsed = ipaddress.ip_address(address)
    except ValueError:
        return False
    return not (
        parsed.is_private
        or parsed.is_loopback
        or parsed.is_link_local
        or parsed.is_multicast
        or parsed.is_reserved
        or parsed.is_unspecified
    )


def _limits(gate: dict[str, Any]) -> dict[str, Any]:
    source = gate.get("resource_limits") or gate.get("limits") or {}
    return {
        "max_pages": int(source.get("max_pages", 1)),
        "max_redirects": int(source.get("max_redirects", 3)),
        "max_response_bytes": int(source.get("max_response_bytes", 5_000_000)),
        "request_timeout_seconds": float(source.get("request_timeout_seconds", 20)),
        "delay_seconds": float(source.get("delay_seconds", 0)),
        "max_depth": int(source.get("max_depth", 0)),
        "concurrency": int(source.get("concurrency", 1)),
    }


def _validate_gate(gate: dict[str, Any] | None, request_id: str) -> str | None:
    if gate is None:
        return "allowing_public_discovery_gate_required"
    if gate.get("discovery_request_id") != request_id:
        return "gate_request_binding_mismatch"
    if gate.get("decision") != "allow":
        return "allowing_public_discovery_gate_required"
    if gate.get("live_network_eligible") is not True:
        return "live_network_eligibility_required"
    if gate.get("robots_allowed") is False:
        return "robots_policy_blocks_execution"
    if gate.get("terms_allowed") is False:
        return "terms_policy_blocks_execution"
    return None


def execute_public_http_capture(
    *,
    actor: str,
    discovery_request_id: str,
    gate_decision_id: str,
    requested_url: str,
    operator_reason: str,
    confirmed: bool,
    transport: Transport,
    resolver: Resolver = _default_resolver,
    sleeper: Sleeper = time.sleep,
    user_agent: str = "SOCMINT-PROJECT/38.5 public-source-capture",
) -> dict[str, Any]:
    actor = _required(actor)
    discovery_request_id = _required(discovery_request_id)
    gate_decision_id = _required(gate_decision_id)
    operator_reason = _required(operator_reason)
    normalized_url = _normalize_url(requested_url)

    if confirmed is not True:
        return blocked("explicit_operator_confirmation_required")
    if not actor:
        return blocked("actor_required")
    if not discovery_request_id or not gate_decision_id:
        return blocked("request_and_gate_binding_required")
    if not operator_reason:
        return blocked("administrative_reason_required")
    if normalized_url is None:
        return blocked("requested_url_invalid")

    request = find_discovery_request(discovery_request_id)
    if request is None:
        return blocked("discovery_request_required")
    gate = find_gate_decision(gate_decision_id)
    gate_error = _validate_gate(gate, discovery_request_id)
    if gate_error:
        return blocked(gate_error)
    assert gate is not None

    manifest = request.get("manifest") or {}
    approved_domains = {
        str(item).lower().rstrip(".")
        for item in (gate.get("approved_domains") or manifest.get("approved_domains") or [])
        if _required(item)
    }
    initial_host = _host(normalized_url)
    if not approved_domains or initial_host not in approved_domains:
        return blocked("requested_domain_not_approved", requested_host=initial_host)

    limits = _limits(gate)
    if limits["max_pages"] != 1 or limits["max_depth"] != 0:
        return blocked("single_page_zero_depth_adapter_required")
    if limits["concurrency"] != 1:
        return blocked("single_concurrency_required")
    if min(limits.values()) < 0:
        return blocked("resource_limits_invalid")

    allowed_types = {
        str(item).lower()
        for item in (gate.get("allowed_content_types") or DEFAULT_ALLOWED_CONTENT_TYPES)
    }
    current_url = normalized_url
    redirects: list[dict[str, Any]] = []
    requests: list[dict[str, Any]] = []
    response: TransportResponse | None = None

    for attempt in range(limits["max_redirects"] + 1):
        host = _host(current_url)
        if host not in approved_domains:
            return blocked("off_domain_redirect_blocked", final_attempt_url=current_url)
        addresses = list(resolver(host))
        if not addresses or any(not _public_ip(address) for address in addresses):
            return blocked("non_public_network_target_blocked", host=host, addresses=addresses)
        if attempt and limits["delay_seconds"]:
            sleeper(limits["delay_seconds"])

        response = transport(
            current_url,
            {
                "accept": ", ".join(sorted(allowed_types)),
                "user-agent": user_agent,
            },
            limits["request_timeout_seconds"],
        )
        final_response_url = _normalize_url(response.url)
        if final_response_url is None or _host(final_response_url) != host:
            return blocked("transport_response_url_invalid")
        headers, header_error = _normalize_headers(response.headers)
        if header_error:
            return blocked(header_error)
        assert headers is not None
        body = bytes(response.body)
        requests.append(
            {
                "url": current_url,
                "status_code": int(response.status_code),
                "elapsed_ms": int(response.elapsed_ms),
            }
        )

        if int(response.status_code) in REDIRECT_CODES:
            location = _required(response.headers.get("location"))
            next_url = _normalize_url(urljoin(current_url, location))
            if next_url is None:
                return blocked("redirect_location_invalid")
            if attempt >= limits["max_redirects"]:
                return blocked("redirect_limit_exceeded")
            if _host(next_url) not in approved_domains:
                return blocked("off_domain_redirect_blocked", redirect_target=next_url)
            redirects.append(
                {"from_url": current_url, "to_url": next_url, "status_code": int(response.status_code)}
            )
            current_url = next_url
            continue

        if len(body) > limits["max_response_bytes"]:
            return blocked("response_size_limit_exceeded", byte_size=len(body))
        media_type = _content_type(headers)
        if media_type not in allowed_types:
            return blocked("response_content_type_blocked", media_type=media_type)
        break
    else:
        return blocked("redirect_limit_exceeded")

    assert response is not None
    capture = {
        "schema": SCHEMA,
        "version": VERSION,
        "discovery_request_id": discovery_request_id,
        "gate_decision_id": gate_decision_id,
        "case_id": manifest.get("case_id"),
        "purpose": manifest.get("purpose"),
        "actor": actor,
        "operator_reason": operator_reason,
        "requested_url": normalized_url,
        "final_url": current_url,
        "redirect_chain": redirects,
        "request_history": requests,
        "response_status": int(response.status_code),
        "response_headers": headers,
        "media_type": media_type,
        "byte_size": len(body),
        "content_sha256": hashlib.sha256(body).hexdigest(),
        "adapter": {
            "name": "official-public-http",
            "version": VERSION,
            "cookies_enabled": False,
            "authentication_enabled": False,
            "automatic_retry_enabled": False,
            "off_domain_following_enabled": False,
            "concurrency": 1,
            "depth": 0,
        },
        "resource_limits": limits,
    }
    capture_sha256 = hashlib.sha256(
        json.dumps(capture, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        **capture,
        "status": "public_http_capture_completed",
        "capture_sha256": capture_sha256,
        "network_request_performed": True,
        "crawler_execution_performed": True,
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
