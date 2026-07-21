from src.socmint import browsertrix_execution_v38_6_1 as service


def _prepared_request(**overrides):
    request = {
        "status": "browsertrix_request_prepared",
        "browser_capture_request_id": "browsertrix-request-a",
        "request_sha256": "a" * 64,
        "execution_id": "execution-a",
        "requested_url": "https://example.test/public-notice",
        "approved_domain": "example.test",
        "storage_target": "private://browsertrix/case-a",
        "resource_limits": {
            "max_pages": 5,
            "max_depth": 1,
            "max_duration_seconds": 120,
            "max_download_bytes": 5_000_000,
            "max_redirects": 2,
            "navigation_timeout_seconds": 20,
            "max_screenshots": 5,
            "concurrency": 1,
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
    }
    request.update(overrides)
    return request


def _outputs():
    return [
        {
            "role": "wacz",
            "filename": "capture.wacz",
            "media_type": "application/wacz",
            "sha256": "1" * 64,
            "byte_size": 100,
        },
        {
            "role": "screenshot",
            "filename": "page.png",
            "media_type": "image/png",
            "sha256": "2" * 64,
            "byte_size": 200,
        },
        {
            "role": "crawl_metadata",
            "filename": "crawl.json",
            "media_type": "application/json",
            "sha256": "3" * 64,
            "byte_size": 300,
        },
    ]


def _raw_result(**overrides):
    result = service.ExecutionResult(
        exit_code=0,
        stdout="fictional Browsertrix completed",
        stderr="",
        timed_out=False,
        cancelled=False,
        started_at="2026-07-21T18:00:00Z",
        completed_at="2026-07-21T18:01:00Z",
        browsertrix_version="1.5.0",
        browser_version="fictional-chromium-1",
        final_url="https://example.test/public-notice",
        redirect_chain=[],
        page_count=1,
        downloaded_bytes=600,
        outputs=_outputs(),
    )
    values = result.__dict__.copy()
    values.update(overrides)
    return service.ExecutionResult(**values)


def test_prepares_pinned_non_privileged_command_plan():
    result = service.prepare_browsertrix_execution(prepared_request=_prepared_request())

    assert result["status"] == "browsertrix_execution_prepared"
    assert result["image"] == service.PINNED_IMAGE
    assert result["executable"] == "crawl"
    assert result["container"]["shell"] is False
    assert result["container"]["privileged"] is False
    assert result["container"]["host_network"] is False
    assert result["container"]["read_only_root"] is True
    assert result["retry_policy"] == {"automatic_retry": False, "max_attempts": 1}
    assert result["container"]["mounts"] == [
        {
            "source": "private://browsertrix/case-a",
            "target": "/crawls",
            "mode": "rw",
            "purpose": "capture-output-only",
        }
    ]
    assert "https://example.test/public-notice" in result["arguments"]
    assert result["browsertrix_process_started"] is False
    assert result["network_request_performed"] is False


def test_execution_plan_is_deterministic_and_rejects_unsafe_runtime():
    first = service.prepare_browsertrix_execution(prepared_request=_prepared_request())
    second = service.prepare_browsertrix_execution(prepared_request=_prepared_request())
    assert first["execution_plan_id"] == second["execution_plan_id"]
    assert first["execution_plan_sha256"] == second["execution_plan_sha256"]

    blocked = service.prepare_browsertrix_execution(
        prepared_request=_prepared_request(), image="browsertrix:latest"
    )
    assert blocked["blockers"] == [{"key": "pinned_browsertrix_image_required"}]

    unsafe = _prepared_request()
    unsafe["browser_policy"] = {
        **unsafe["browser_policy"],
        "cookies_supplied": True,
    }
    blocked = service.prepare_browsertrix_execution(prepared_request=unsafe)
    assert blocked["blockers"] == [{"key": "unsafe_browser_policy_prohibited"}]


def test_fake_executor_runs_once_and_records_complete_lifecycle():
    plan = service.prepare_browsertrix_execution(prepared_request=_prepared_request())
    calls = []

    def fake_executor(received):
        calls.append(received)
        return _raw_result()

    result = service.execute_browsertrix_capture(
        execution_plan=plan, executor=fake_executor
    )

    assert len(calls) == 1
    assert result["status"] == "browsertrix_execution_completed"
    assert result["attempt_count"] == 1
    assert result["automatic_retry_performed"] is False
    assert result["browsertrix_process_started"] is True
    assert result["network_request_performed"] is True
    assert len(result["execution_result_sha256"]) == 64


def test_failed_timeout_is_not_retried_or_validated():
    plan = service.prepare_browsertrix_execution(prepared_request=_prepared_request())
    calls = []

    def fake_executor(received):
        calls.append(received)
        return _raw_result(exit_code=124, timed_out=True)

    result = service.execute_browsertrix_capture(
        execution_plan=plan, executor=fake_executor
    )
    assert len(calls) == 1
    assert result["status"] == "browsertrix_execution_failed"
    assert result["attempt_count"] == 1
    assert result["automatic_retry_performed"] is False

    validated = service.validate_controlled_browsertrix_execution(
        execution_plan=plan, execution_result=result
    )
    assert validated["blockers"] == [
        {"key": "successful_browsertrix_execution_required"}
    ]


def test_validation_delegates_only_after_exact_plan_binding(monkeypatch):
    plan = service.prepare_browsertrix_execution(prepared_request=_prepared_request())
    execution = service.execute_browsertrix_capture(
        execution_plan=plan, executor=lambda _: _raw_result()
    )
    calls = []

    def fake_validate(**kwargs):
        calls.append(kwargs)
        return {
            "status": "browsertrix_result_validated",
            "preservation_manifest_sha256": "f" * 64,
        }

    monkeypatch.setattr(service, "validate_browsertrix_result", fake_validate)
    result = service.validate_controlled_browsertrix_execution(
        execution_plan=plan, execution_result=execution
    )
    assert result["status"] == "browsertrix_result_validated"
    assert len(calls) == 1
    assert calls[0]["browser_capture_request_id"] == "browsertrix-request-a"
    assert calls[0]["completion_status"] == "completed"

    tampered = {**execution, "execution_plan_sha256": "0" * 64}
    result = service.validate_controlled_browsertrix_execution(
        execution_plan=plan, execution_result=tampered
    )
    assert result["blockers"] == [{"key": "execution_plan_hash_mismatch"}]
    assert len(calls) == 1


def test_executor_exception_becomes_explicit_failure_without_retry():
    plan = service.prepare_browsertrix_execution(prepared_request=_prepared_request())
    calls = []

    def failing_executor(received):
        calls.append(received)
        raise RuntimeError("fictional executor failure")

    result = service.execute_browsertrix_capture(
        execution_plan=plan, executor=failing_executor
    )
    assert len(calls) == 1
    assert result["status"] == "browsertrix_execution_failed"
    assert result["blockers"] == [{"key": "browsertrix_executor_failed"}]
    assert result["automatic_retry_performed"] is False
