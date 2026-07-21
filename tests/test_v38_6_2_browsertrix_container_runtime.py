from __future__ import annotations

from socmint.browsertrix_container_runtime_v38_6_2 import (
    ProcessOutcome,
    ResolvedStorageTarget,
    RuntimeInspection,
    execute_container_runtime,
    prepare_container_runtime,
)
from socmint.browsertrix_execution_v38_6_1 import ExecutionResult


DIGEST = "sha256:" + "a" * 64
IMAGE = f"webrecorder/browsertrix-crawler@{DIGEST}"


def execution_plan() -> dict:
    return {
        "status": "browsertrix_execution_prepared",
        "execution_plan_id": "browsertrix-execution-test",
        "execution_plan_sha256": "b" * 64,
        "browser_capture_request_id": "browsertrix-request-test",
        "request_sha256": "c" * 64,
        "execution_id": "execution-test",
        "requested_url": "https://example.test/",
        "approved_domain": "example.test",
        "image": "webrecorder/browsertrix-crawler:1.5.0",
        "executable": "crawl",
        "arguments": ["--url", "https://example.test/", "--workers", "1"],
        "container": {
            "privileged": False,
            "host_network": False,
            "read_only_root": True,
            "shell": False,
            "cpu_limit": 1.0,
            "memory_limit_mb": 1024,
            "process_limit": 128,
            "mounts": [
                {"source": "private://case/capture", "target": "/crawls"}
            ],
        },
        "retry_policy": {"automatic_retry": False, "max_attempts": 1},
        "prepared_request": {
            "case_id": "case-test",
            "resource_limits": {"max_duration_seconds": 60},
        },
    }


def policy(**overrides) -> dict:
    value = {
        "runtime_enabled": True,
        "operator_confirmed": True,
        "execution_plan_sha256": "b" * 64,
        "execution_mode": "deployment_certification",
        "certification_run": True,
        "deployment_id": "deployment-test",
        "execution_requested_at": "2026-07-21T20:00:00Z",
        "actor": "deployment-reviewer",
        "runtime": "docker",
        "image_digest": DIGEST,
        "network_name": "socmint-browsertrix-egress",
        "approved_storage_root": "/srv/socmint/browsertrix",
        "network_configured": True,
        "egress_policy_verified": True,
        "dns_policy_verified": True,
        "approved_target_binding_verified": True,
    }
    value.update(overrides)
    return value


def storage_resolver(uri: str) -> ResolvedStorageTarget:
    return ResolvedStorageTarget(
        logical_uri=uri,
        host_path="/srv/socmint/browsertrix/case/capture",
        approved_root="/srv/socmint/browsertrix",
        created_empty=True,
        symlink_safe=True,
        restrictive_permissions=True,
    )


def runtime_inspector(runtime: str, image_reference: str) -> RuntimeInspection:
    return RuntimeInspection(
        runtime=runtime,
        binary_path="/usr/bin/docker",
        runtime_version="Docker version test",
        image_reference=image_reference,
        local_image_digest=DIGEST,
        image_present_locally=True,
    )


def test_runtime_is_disabled_by_default() -> None:
    result = prepare_container_runtime(
        execution_plan=execution_plan(),
        deployment_policy=policy(runtime_enabled=False),
        storage_resolver=storage_resolver,
        runtime_inspector=runtime_inspector,
    )
    assert result["status"] == "blocked"
    assert result["blockers"] == [{"key": "browsertrix_runtime_disabled"}]
    assert result["container_started"] is False


def test_runtime_requires_exact_plan_binding() -> None:
    result = prepare_container_runtime(
        execution_plan=execution_plan(),
        deployment_policy=policy(execution_plan_sha256="wrong"),
        storage_resolver=storage_resolver,
        runtime_inspector=runtime_inspector,
    )
    assert result["blockers"] == [
        {"key": "runtime_execution_plan_binding_mismatch"}
    ]


def test_runtime_requires_explicit_certification_mode_and_test_target() -> None:
    result = prepare_container_runtime(
        execution_plan=execution_plan(),
        deployment_policy=policy(execution_mode=""),
        storage_resolver=storage_resolver,
        runtime_inspector=runtime_inspector,
    )
    assert result["blockers"] == [{"key": "explicit_runtime_execution_mode_required"}]

    plan = execution_plan()
    plan["requested_url"] = "https://example.com/"
    result = prepare_container_runtime(
        execution_plan=plan,
        deployment_policy=policy(),
        storage_resolver=storage_resolver,
        runtime_inspector=runtime_inspector,
    )
    assert result["blockers"] == [
        {"key": "fictional_test_target_required_for_certification"}
    ]


def test_runtime_requires_full_network_containment_proof() -> None:
    result = prepare_container_runtime(
        execution_plan=execution_plan(),
        deployment_policy=policy(egress_policy_verified=False),
        storage_resolver=storage_resolver,
        runtime_inspector=runtime_inspector,
    )
    assert result["blockers"] == [
        {"key": "verified_network_containment_required"}
    ]


def test_runtime_requires_local_digest_and_storage_root_match() -> None:
    def mismatch(runtime: str, image_reference: str) -> RuntimeInspection:
        inspected = runtime_inspector(runtime, image_reference)
        return RuntimeInspection(
            **{
                **inspected.__dict__,
                "local_image_digest": "sha256:" + "d" * 64,
            }
        )

    result = prepare_container_runtime(
        execution_plan=execution_plan(),
        deployment_policy=policy(),
        storage_resolver=storage_resolver,
        runtime_inspector=mismatch,
    )
    assert result["blockers"] == [{"key": "local_image_digest_mismatch"}]

    result = prepare_container_runtime(
        execution_plan=execution_plan(),
        deployment_policy=policy(approved_storage_root="/other/root"),
        storage_resolver=storage_resolver,
        runtime_inspector=runtime_inspector,
    )
    assert result["blockers"] == [{"key": "approved_storage_root_mismatch"}]


def test_prepared_command_is_fixed_and_hardened() -> None:
    result = prepare_container_runtime(
        execution_plan=execution_plan(),
        deployment_policy=policy(),
        storage_resolver=storage_resolver,
        runtime_inspector=runtime_inspector,
    )
    assert result["status"] == "browsertrix_container_runtime_prepared"
    assert result["execution_mode"] == "deployment_certification"
    assert result["shell"] is False
    assert result["image_reference"] == IMAGE
    assert result["image_pull_allowed"] is False
    assert result["automatic_retry"] is False
    assert result["max_attempts"] == 1
    command = result["command"]
    assert command[0] == "/usr/bin/docker"
    assert "--privileged" not in command
    assert "--read-only" in command
    assert ["--cap-drop", "ALL"] == command[
        command.index("--cap-drop") : command.index("--cap-drop") + 2
    ]
    assert ["--security-opt", "no-new-privileges"] == command[
        command.index("--security-opt") : command.index("--security-opt") + 2
    ]
    assert "--network" in command
    assert IMAGE in command
    assert "pull" not in command


def test_failed_process_is_single_attempt_and_quarantined() -> None:
    prepared = prepare_container_runtime(
        execution_plan=execution_plan(),
        deployment_policy=policy(),
        storage_resolver=storage_resolver,
        runtime_inspector=runtime_inspector,
    )
    calls = []

    def runner(command: list[str], timeout: int) -> ProcessOutcome:
        calls.append((command, timeout))
        return ProcessOutcome(
            exit_code=124,
            stdout="",
            stderr="timeout",
            timed_out=True,
        )

    def should_not_load(*args):
        raise AssertionError("result loader must not run after process failure")

    result = execute_container_runtime(
        runtime_request=prepared,
        process_runner=runner,
        result_loader=should_not_load,
    )
    assert len(calls) == 1
    assert result["status"] == "browsertrix_container_execution_failed"
    assert result["automatic_retry_performed"] is False
    assert result["quarantine_required"] is True
    assert result["cleanup_required"] is True


def test_success_returns_existing_execution_result_contract() -> None:
    prepared = prepare_container_runtime(
        execution_plan=execution_plan(),
        deployment_policy=policy(),
        storage_resolver=storage_resolver,
        runtime_inspector=runtime_inspector,
    )

    def runner(command: list[str], timeout: int) -> ProcessOutcome:
        return ProcessOutcome(exit_code=0, stdout="completed", stderr="")

    expected = ExecutionResult(
        exit_code=0,
        stdout="completed",
        stderr="",
        timed_out=False,
        cancelled=False,
        started_at="2026-07-21T18:00:00+00:00",
        completed_at="2026-07-21T18:01:00+00:00",
        browsertrix_version="1.5.0",
        browser_version="test-browser",
        final_url="https://example.test/",
        redirect_chain=[],
        page_count=1,
        downloaded_bytes=100,
        outputs=[],
    )

    def loader(plan, storage, outcome):
        assert plan["execution_plan_id"] == "browsertrix-execution-test"
        assert storage.logical_uri == "private://case/capture"
        assert outcome.exit_code == 0
        return expected

    result = execute_container_runtime(
        runtime_request=prepared,
        process_runner=runner,
        result_loader=loader,
    )
    assert result["status"] == "browsertrix_container_execution_completed"
    assert result["attempt_count"] == 1
    assert result["execution_result"] == expected
    assert result["quarantine_required"] is False
