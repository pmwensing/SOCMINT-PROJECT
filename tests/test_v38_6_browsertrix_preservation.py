from src.socmint import browsertrix_preservation_v38_6 as service


def _request():
    return {
        "discovery_request_id": "request-a",
        "manifest": {
            "case_id": "case-a",
            "purpose": "Preserve a fictional public page.",
            "approved_domains": ["example.test"],
            "collection_job_binding": {"collection_job_id": "job-a", "attempt_number": 1},
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
    }
    gate.update(overrides)
    return gate


def _preflight(**overrides):
    value = {
        "status": "public_http_capture_completed",
        "discovery_request_id": "request-a",
        "gate_decision_id": "gate-a",
        "requested_url": "https://example.test/public",
        "final_url": "https://example.test/public",
        "capture_sha256": "a" * 64,
        "content_sha256": "b" * 64,
    }
    value.update(overrides)
    return value


def _limits(**overrides):
    value = {
        "max_pages": 5,
        "max_depth": 1,
        "max_duration_seconds": 120,
        "max_download_bytes": 5_000_000,
        "max_redirects": 3,
        "navigation_timeout_seconds": 20,
        "max_screenshots": 5,
        "concurrency": 1,
    }
    value.update(overrides)
    return value


def _prepare(monkeypatch, **overrides):
    monkeypatch.setattr(service, "find_discovery_request", lambda value: _request())
    monkeypatch.setattr(service, "find_gate_decision", lambda value: _gate())
    payload = {
        "actor": "admin",
        "discovery_request_id": "request-a",
        "gate_decision_id": "gate-a",
        "public_http_capture": _preflight(),
        "requested_url": "https://example.test/public",
        "javascript_justification": "The fictional page requires client-side rendering.",
        "operator_reason": "Preserve the approved public page.",
        "execution_id": "execution-a",
        "storage_target": "private://captures/case-a",
        "resource_limits": _limits(),
        "allowed_content_types": ["text/html", "image/png"],
        "confirmed": True,
    }
    payload.update(overrides)
    return service.prepare_browsertrix_request(**payload)


def _outputs():
    return [
        {"role": "wacz", "filename": "capture.wacz", "media_type": "application/wacz", "sha256": "1" * 64, "byte_size": 1000},
        {"role": "screenshot", "filename": "page.png", "media_type": "image/png", "sha256": "2" * 64, "byte_size": 500},
        {"role": "crawl_metadata", "filename": "metadata.json", "media_type": "application/json", "sha256": "3" * 64, "byte_size": 200},
    ]


def test_v38_6_prepares_deterministic_offline_request(monkeypatch):
    first = _prepare(monkeypatch)
    second = _prepare(monkeypatch)

    assert first["status"] == "browsertrix_request_prepared"
    assert first["request_sha256"] == second["request_sha256"]
    assert first["browser_capture_request_id"] == second["browser_capture_request_id"]
    assert first["browsertrix_process_started"] is False
    assert first["network_request_performed"] is False
    assert first["browser_policy"] == {
        "authentication_enabled": False,
        "credentials_enabled": False,
        "cookies_supplied": False,
        "saved_profile_enabled": False,
        "form_submission_enabled": False,
        "file_upload_enabled": False,
        "captcha_bypass_enabled": False,
        "automatic_retry_enabled": False,
        "off_domain_navigation_enabled": False,
    }


def test_v38_6_blocks_missing_preflight_and_policy_failure(monkeypatch):
    result = _prepare(monkeypatch, public_http_capture=None)
    assert result["blockers"] == [{"key": "v38_5_public_http_preflight_required"}]

    monkeypatch.setattr(service, "find_discovery_request", lambda value: _request())
    monkeypatch.setattr(service, "find_gate_decision", lambda value: _gate(decision="block"))
    result = service.prepare_browsertrix_request(
        actor="admin", discovery_request_id="request-a", gate_decision_id="gate-a",
        public_http_capture=_preflight(), requested_url="https://example.test/public",
        javascript_justification="Client rendering required.", operator_reason="Preserve.",
        execution_id="execution-a", storage_target="private://captures/case-a",
        resource_limits=_limits(), allowed_content_types=["text/html"], confirmed=True,
    )
    assert result["blockers"] == [{"key": "allowing_live_network_gate_required"}]


def test_v38_6_blocks_unsafe_scope_and_storage(monkeypatch):
    result = _prepare(monkeypatch, storage_target="file:///tmp/capture")
    assert result["blockers"] == [{"key": "approved_private_storage_target_required"}]

    result = _prepare(monkeypatch, resource_limits=_limits(max_pages=26))
    assert result["blockers"] == [{"key": "browser_scope_limits_exceeded"}]

    result = _prepare(monkeypatch, requested_url="https://outside.test/public")
    assert result["blockers"] == [{"key": "v38_5_url_binding_mismatch"}]


def test_v38_6_validates_hash_bound_preservation_result(monkeypatch):
    prepared = _prepare(monkeypatch)
    result = service.validate_browsertrix_result(
        prepared_request=prepared,
        browser_capture_request_id=prepared["browser_capture_request_id"],
        request_sha256=prepared["request_sha256"],
        execution_id="execution-a",
        requested_url="https://example.test/public",
        final_url="https://example.test/public-rendered",
        redirect_chain=[],
        started_at="2026-07-21T12:00:00Z",
        completed_at="2026-07-21T12:01:00Z",
        browsertrix_version="1.0",
        browser_version="chromium-fictional",
        page_count=1,
        downloaded_bytes=1700,
        outputs=_outputs(),
        completion_status="completed",
    )

    assert result["status"] == "browsertrix_result_validated"
    assert len(result["preservation_manifest_sha256"]) == 64
    assert result["browsertrix_process_started"] is True
    assert result["artifact_registered"] is False
    assert result["observation_created"] is False
    assert {item["role"] for item in result["outputs"]} == {"wacz", "screenshot", "crawl_metadata"}


def test_v38_6_blocks_off_domain_missing_output_and_limit_excess(monkeypatch):
    prepared = _prepare(monkeypatch)
    base = {
        "prepared_request": prepared,
        "browser_capture_request_id": prepared["browser_capture_request_id"],
        "request_sha256": prepared["request_sha256"],
        "execution_id": "execution-a",
        "requested_url": "https://example.test/public",
        "final_url": "https://example.test/public",
        "redirect_chain": [],
        "started_at": "2026-07-21T12:00:00Z",
        "completed_at": "2026-07-21T12:01:00Z",
        "browsertrix_version": "1.0",
        "browser_version": "chromium-fictional",
        "page_count": 1,
        "downloaded_bytes": 1700,
        "outputs": _outputs(),
        "completion_status": "completed",
    }

    result = service.validate_browsertrix_result(**{**base, "final_url": "https://outside.test/page"})
    assert result["blockers"] == [{"key": "off_domain_browser_result_blocked"}]

    result = service.validate_browsertrix_result(**{**base, "outputs": _outputs()[:-1]})
    assert result["blockers"] == [{"key": "required_preservation_outputs_missing"}]

    result = service.validate_browsertrix_result(**{**base, "page_count": 6})
    assert result["blockers"] == [{"key": "browser_page_limit_exceeded"}]

    result = service.validate_browsertrix_result(**{**base, "request_sha256": "0" * 64})
    assert result["blockers"] == [{"key": "browser_request_hash_mismatch"}]
