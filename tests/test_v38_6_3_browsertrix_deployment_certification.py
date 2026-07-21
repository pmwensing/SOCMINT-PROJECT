from __future__ import annotations

from src.socmint import browsertrix_preservation_v38_6 as preservation
from src.socmint import browsertrix_deployment_certification_v38_6_3 as service
from src.socmint.browsertrix_execution_v38_6_1 import ExecutionResult


FIXTURE_HASH = "a" * 64
RUNTIME_HASH = "b" * 64
PLAN_HASH = "c" * 64


def _prepared_request() -> dict:
    return {
        "status": "browsertrix_request_prepared",
        "browser_capture_request_id": "browsertrix-request-certification",
        "request_sha256": "d" * 64,
        "execution_id": "execution-certification",
        "requested_url": "http://fixture.example.test/public-notice",
        "approved_domain": "fixture.example.test",
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
    }


def _execution_plan() -> dict:
    return {
        "status": "browsertrix_execution_prepared",
        "execution_plan_id": "browsertrix-execution-certification",
        "execution_plan_sha256": PLAN_HASH,
        "browser_capture_request_id": "browsertrix-request-certification",
        "request_sha256": "d" * 64,
        "execution_id": "execution-certification",
        "requested_url": "http://fixture.example.test/public-notice",
        "approved_domain": "fixture.example.test",
        "image": "webrecorder/browsertrix-crawler:1.5.0",
        "executable": "crawl",
        "arguments": [
            "--url",
            "http://fixture.example.test/public-notice",
            "--workers",
            "1",
        ],
        "container": {
            "shell": False,
            "privileged": False,
            "host_network": False,
            "read_only_root": True,
        },
        "retry_policy": {"automatic_retry": False, "max_attempts": 1},
        "prepared_request": _prepared_request(),
    }


def _runtime_request() -> dict:
    return {
        "status": "browsertrix_container_runtime_prepared",
        "runtime_request_id": "browsertrix-runtime-certification",
        "runtime_sha256": RUNTIME_HASH,
        "runtime_enabled": True,
        "execution_plan_id": "browsertrix-execution-certification",
        "execution_plan_sha256": PLAN_HASH,
        "runtime": "docker",
        "runtime_version": "Docker test",
        "image_reference": "webrecorder/browsertrix-crawler@sha256:" + "e" * 64,
        "image_digest": "sha256:" + "e" * 64,
        "network_name": "socmint-browsertrix-certification",
        "network_controls": {
            "network_configured": True,
            "egress_policy_verified": True,
            "dns_policy_verified": True,
            "approved_target_binding_verified": True,
        },
        "storage": {
            "logical_uri": "private://certification/run-a",
            "host_path": "/srv/socmint/browsertrix/certification/run-a",
            "approved_root": "/srv/socmint/browsertrix",
        },
        "execution_plan": _execution_plan(),
    }


def _prepare(**overrides) -> dict:
    values = {
        "runtime_request": _runtime_request(),
        "actor": "deployment-reviewer",
        "certification_environment": "isolated_deployment",
        "fixture_url": "http://fixture.example.test/public-notice",
        "fixture_content_sha256": FIXTURE_HASH,
        "external_probe_url": "https://blocked-probe.invalid/",
        "reason": "Certify isolated deployment controls with fictional fixtures.",
        "operator_confirmed": True,
        "standard_ci_live_execution": False,
        "production_enablement_requested": False,
    }
    values.update(overrides)
    return service.prepare_deployment_certification(**values)


def _outputs() -> list[dict]:
    return [
        {
            "role": "wacz",
            "filename": "capture.wacz",
            "media_type": "application/wacz",
            "sha256": "1" * 64,
            "byte_size": 1000,
        },
        {
            "role": "screenshot_archive",
            "filename": "screenshots.warc.gz",
            "media_type": "application/gzip",
            "sha256": "2" * 64,
            "byte_size": 500,
        },
        {
            "role": "crawl_metadata",
            "filename": "pages.jsonl",
            "media_type": "application/x-ndjson",
            "sha256": "3" * 64,
            "byte_size": 200,
        },
    ]


def _execution_result() -> ExecutionResult:
    return ExecutionResult(
        exit_code=0,
        stdout="fictional deployment certification completed",
        stderr="",
        timed_out=False,
        cancelled=False,
        started_at="2026-07-21T20:00:00Z",
        completed_at="2026-07-21T20:01:00Z",
        browsertrix_version="1.5.0",
        browser_version="fictional-chromium",
        final_url="http://fixture.example.test/public-notice",
        redirect_chain=[],
        page_count=1,
        downloaded_bytes=1700,
        outputs=_outputs(),
    )


def _observation(plan: dict, **overrides) -> service.DeploymentCertificationObservation:
    values = {
        "certification_plan_id": plan["certification_plan_id"],
        "certification_plan_sha256": plan["certification_plan_sha256"],
        "runtime_request_id": plan["runtime_request_id"],
        "runtime_sha256": plan["runtime_sha256"],
        "fixture_url": plan["fixture_url"],
        "fixture_status": 200,
        "fixture_content_sha256": FIXTURE_HASH,
        "external_probe_url": plan["external_probe_url"],
        "external_probe_blocked": True,
        "external_probe_response_received": False,
        "network_isolated": True,
        "egress_policy_enforced": True,
        "dns_policy_enforced": True,
        "target_binding_enforced": True,
        "successful_hosts": ["fixture.example.test"],
        "attempt_count": 1,
        "automatic_retry_performed": False,
        "storage_host_path": "/srv/socmint/browsertrix/certification/run-a",
        "storage_approved_root": "/srv/socmint/browsertrix",
        "storage_cleanup_completed": True,
        "output_quarantine_required": False,
        "execution_result": _execution_result(),
    }
    values.update(overrides)
    return service.DeploymentCertificationObservation(**values)


def test_preservation_accepts_real_browsertrix_output_profile() -> None:
    outputs, error = preservation._outputs(_outputs())
    assert error is None
    assert outputs is not None
    assert {item["role"] for item in outputs} == {
        "wacz",
        "screenshot_archive",
        "crawl_metadata",
    }

    missing_screenshot_evidence = [item for item in _outputs() if item["role"] != "screenshot_archive"]
    outputs, error = preservation._outputs(missing_screenshot_evidence)
    assert outputs is None
    assert error == "required_preservation_outputs_missing"


def test_prepare_is_deterministic_and_never_enables_production() -> None:
    first = _prepare()
    second = _prepare()
    assert first["status"] == "browsertrix_deployment_certification_prepared"
    assert first["certification_plan_id"] == second["certification_plan_id"]
    assert first["certification_plan_sha256"] == second["certification_plan_sha256"]
    assert first["standard_ci_live_execution"] is False
    assert first["production_enablement_requested"] is False
    assert first["production_enablement_granted"] is False


def test_prepare_blocks_standard_ci_and_nonfictional_targets() -> None:
    result = _prepare(standard_ci_live_execution=True)
    assert result["blockers"] == [{"key": "standard_ci_live_execution_prohibited"}]

    result = _prepare(fixture_url="https://example.com/")
    assert result["blockers"] == [{"key": "fictional_test_fixture_url_required"}]

    result = _prepare(external_probe_url="https://example.com/")
    assert result["blockers"] == [{"key": "blocked_external_probe_url_required"}]


def test_certification_passes_only_with_fixture_and_containment_proofs() -> None:
    plan = _prepare()
    calls = []

    def executor(received):
        calls.append(received)
        return _observation(received)

    result = service.execute_deployment_certification(
        certification_plan=plan,
        executor=executor,
    )
    assert len(calls) == 1
    assert result["status"] == "browsertrix_deployment_certification_passed"
    assert result["deployment_certification_passed"] is True
    assert result["production_enablement_granted"] is False
    assert result["required_proofs"] == {
        "fictional_fixture_capture": True,
        "fixture_content_hash_match": True,
        "external_egress_blocked": True,
        "dns_policy_enforced": True,
        "egress_policy_enforced": True,
        "approved_target_binding_enforced": True,
        "single_attempt_only": True,
        "storage_cleanup_completed": True,
        "preservation_result_validated": True,
    }
    assert len(result["certification_sha256"]) == 64
    assert result["artifact_registered"] is False
    assert result["observation_created"] is False


def test_unblocked_external_probe_fails_and_is_not_retried() -> None:
    plan = _prepare()
    calls = []

    def executor(received):
        calls.append(received)
        return _observation(
            received,
            external_probe_blocked=False,
            external_probe_response_received=True,
            successful_hosts=["fixture.example.test", "blocked-probe.invalid"],
        )

    result = service.execute_deployment_certification(
        certification_plan=plan,
        executor=executor,
    )
    assert len(calls) == 1
    assert result["blockers"] == [{"key": "external_egress_probe_not_blocked"}]
    assert result["external_egress_succeeded"] is True
    assert result["automatic_retry_performed"] is False
    assert result["production_enablement_granted"] is False


def test_executor_exception_is_explicit_and_requires_quarantine() -> None:
    plan = _prepare()
    calls = []

    def executor(received):
        calls.append(received)
        raise RuntimeError("fictional certification failure")

    result = service.execute_deployment_certification(
        certification_plan=plan,
        executor=executor,
    )
    assert len(calls) == 1
    assert result["status"] == "browsertrix_deployment_certification_failed"
    assert result["blockers"] == [
        {"key": "deployment_certification_executor_failed"}
    ]
    assert result["quarantine_required"] is True
    assert result["cleanup_required"] is True
    assert result["production_enablement_granted"] is False
