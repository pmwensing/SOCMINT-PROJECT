from src.socmint import public_http_crawler_v38_5 as service


def _request():
    return {
        "discovery_request_id": "request-a",
        "manifest": {
            "case_id": "case-a",
            "purpose": "Preserve a fictional official notice.",
            "approved_domains": ["example.test"],
        },
    }


def _gate(**overrides):
    gate = {
        "gate_decision_id": "gate-a",
        "discovery_request_id": "request-a",
        "decision": "allow",
        "live_network_eligible": True,
        "robots_allowed": True,
        "terms_allowed": True,
        "approved_domains": ["example.test"],
        "allowed_content_types": ["text/html", "application/pdf"],
        "resource_limits": {
            "max_pages": 1,
            "max_redirects": 2,
            "max_response_bytes": 1024,
            "request_timeout_seconds": 10,
            "delay_seconds": 0,
            "max_depth": 0,
            "concurrency": 1,
        },
    }
    gate.update(overrides)
    return gate


def _configure(monkeypatch, *, request=None, gate=None):
    monkeypatch.setattr(service, "find_discovery_request", lambda request_id: request)
    monkeypatch.setattr(service, "find_gate_decision", lambda gate_id: gate)


def _payload(**overrides):
    payload = {
        "actor": "admin",
        "discovery_request_id": "request-a",
        "gate_decision_id": "gate-a",
        "requested_url": "https://example.test/notices/1",
        "operator_reason": "Capture the approved fictional official page.",
        "confirmed": True,
        "resolver": lambda host: ["93.184.216.34"],
        "sleeper": lambda seconds: None,
    }
    payload.update(overrides)
    return payload


def test_v38_5_completes_hash_bound_single_page_capture(monkeypatch):
    _configure(monkeypatch, request=_request(), gate=_gate())
    calls = []

    def transport(url, headers, timeout):
        calls.append((url, headers, timeout))
        return service.TransportResponse(
            status_code=200,
            url=url,
            headers={"content-type": "text/html; charset=utf-8", "etag": "fictional"},
            body=b"<html>fictional official notice</html>",
            elapsed_ms=12,
        )

    result = service.execute_public_http_capture(**_payload(transport=transport))

    assert result["status"] == "public_http_capture_completed"
    assert len(result["capture_sha256"]) == 64
    assert len(result["content_sha256"]) == 64
    assert result["requested_url"] == "https://example.test/notices/1"
    assert result["final_url"] == result["requested_url"]
    assert result["media_type"] == "text/html"
    assert result["adapter"]["cookies_enabled"] is False
    assert result["adapter"]["authentication_enabled"] is False
    assert result["adapter"]["automatic_retry_enabled"] is False
    assert result["artifact_registered"] is False
    assert result["observation_created"] is False
    assert calls[0][1].get("cookie") is None
    assert calls[0][1].get("authorization") is None


def test_v38_5_records_approved_same_domain_redirect(monkeypatch):
    _configure(monkeypatch, request=_request(), gate=_gate())

    def transport(url, headers, timeout):
        if url.endswith("/1"):
            return service.TransportResponse(
                status_code=302,
                url=url,
                headers={"location": "/notices/1-final", "set-cookie": "discard=1"},
                body=b"",
            )
        return service.TransportResponse(
            status_code=200,
            url=url,
            headers={"content-type": "application/pdf"},
            body=b"%PDF fictional",
        )

    result = service.execute_public_http_capture(**_payload(transport=transport))

    assert result["status"] == "public_http_capture_completed"
    assert result["final_url"].endswith("/notices/1-final")
    assert result["redirect_chain"][0]["status_code"] == 302
    assert "set-cookie" not in result["response_headers"]


def test_v38_5_blocks_without_live_network_gate(monkeypatch):
    _configure(monkeypatch, request=_request(), gate=_gate(live_network_eligible=False))
    result = service.execute_public_http_capture(
        **_payload(transport=lambda *args: (_ for _ in ()).throw(AssertionError("must not fetch")))
    )
    assert result["blockers"] == [{"key": "live_network_eligibility_required"}]
    assert result["network_request_performed"] is False


def test_v38_5_blocks_private_network_and_off_domain_redirect(monkeypatch):
    _configure(monkeypatch, request=_request(), gate=_gate())
    result = service.execute_public_http_capture(
        **_payload(
            resolver=lambda host: ["127.0.0.1"],
            transport=lambda *args: (_ for _ in ()).throw(AssertionError("must not fetch")),
        )
    )
    assert result["blockers"] == [{"key": "non_public_network_target_blocked"}]

    def redirect_transport(url, headers, timeout):
        return service.TransportResponse(
            status_code=302,
            url=url,
            headers={"location": "https://unapproved.test/private"},
            body=b"",
        )

    result = service.execute_public_http_capture(**_payload(transport=redirect_transport))
    assert result["blockers"] == [{"key": "off_domain_redirect_blocked"}]


def test_v38_5_blocks_content_and_size_limit_violations(monkeypatch):
    _configure(monkeypatch, request=_request(), gate=_gate())

    result = service.execute_public_http_capture(
        **_payload(
            transport=lambda url, headers, timeout: service.TransportResponse(
                200, url, {"content-type": "application/zip"}, b"zip"
            )
        )
    )
    assert result["blockers"] == [{"key": "response_content_type_blocked"}]

    result = service.execute_public_http_capture(
        **_payload(
            transport=lambda url, headers, timeout: service.TransportResponse(
                200, url, {"content-type": "text/html"}, b"x" * 1025
            )
        )
    )
    assert result["blockers"] == [{"key": "response_size_limit_exceeded"}]


def test_v38_5_requires_single_page_zero_depth_and_concurrency(monkeypatch):
    _configure(
        monkeypatch,
        request=_request(),
        gate=_gate(
            resource_limits={
                "max_pages": 2,
                "max_redirects": 2,
                "max_response_bytes": 1024,
                "request_timeout_seconds": 10,
                "delay_seconds": 0,
                "max_depth": 1,
                "concurrency": 2,
            }
        ),
    )
    result = service.execute_public_http_capture(
        **_payload(transport=lambda *args: (_ for _ in ()).throw(AssertionError("must not fetch")))
    )
    assert result["blockers"] == [{"key": "single_page_zero_depth_adapter_required"}]
