from __future__ import annotations

from src.socmint import browsertrix_container_runtime_v38_6_2 as runtime
from src.socmint import browsertrix_production_enablement_v38_6_4 as service
from src.socmint.browsertrix_execution_v38_6_1 import ExecutionResult


DIGEST = "sha256:" + "a" * 64
PLAN_HASH = "b" * 64
CERT_PLAN_HASH = "c" * 64
CERT_RUNTIME_HASH = "d" * 64


def _limits(**overrides) -> dict:
    value = {
        "max_pages": 5,
        "max_depth": 1,
        "max_duration_seconds": 120,
        "max_download_bytes": 5_000_000,
        "max_redirects": 2,
        "navigation_timeout_seconds": 20,
        "max_screenshots": 5,
        "concurrency": 1,
    }
    value.update(overrides)
    return value


def _certification_execution_plan() -> dict:
    return {
        "status": "browsertrix_execution_prepared",
        "execution_plan_id": "certification-execution-plan",
        "execution_plan_sha256": "e" * 64,
        "requested_url": "http://fixture.example.test/public",
        "approved_domain": "fixture.example.test",
        "prepared_request": {
            "case_id": "case-certification",
            "resource_limits": _limits(),
        },
    }


def _certification_runtime_request() -> dict:
    return {
        "runtime_request_id": "certification-runtime-request",
        "runtime_sha256": CERT_RUNTIME_HASH,
        "runtime": "docker",
        "image_digest": DIGEST,
        "network_name": "socmint-browsertrix-egress",
        "storage": {
            "approved_root": "/srv/socmint/browsertrix",
            "host_path": "/srv/socmint/browsertrix/certification/run-a",
        },
        "execution_plan": _certification_execution_plan(),
    }


def _certification_plan() -> dict:
    return {
        "status": "browsertrix_deployment_certification_prepared",
        "certification_plan_id": "certification-plan-a",
        "certification_plan_sha256": CERT_PLAN_HASH,
        "runtime_request_id": "certification-runtime-request",
        "runtime_sha256": CERT_RUNTIME_HASH,
        "runtime_request": _certification_runtime_request(),
    }


def _certification_result() -> dict:
    return {
        "status": "browsertrix_deployment_certification_passed",
        "certification_id": "certification-result-a",
        "certification_sha256": "f" * 64,
        "production_enablement_granted": False,
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
        "evidence": {
            "certification_plan_id": "certification-plan-a",
            "certification_plan_sha256": CERT_PLAN_HASH,
            "runtime_request_id": "certification-runtime-request",
            "runtime_sha256": CERT_RUNTIME_HASH,
        },
    }


def _production_execution_plan(**overrides) -> dict:
    plan = {
        "status": "browsertrix_execution_prepared",
        "execution_plan_id": "production-execution-plan-a",
        "execution_plan_sha256": PLAN_HASH,
        "browser_capture_request_id": "browsertrix-request-production-a",
        "request_sha256": "1" * 64,
        "execution_id": "case-execution-a",
        "requested_url": "https://records.city.example/public-notice",
        "approved_domain": "records.city.example",
        "image": "webrecorder/browsertrix-crawler:1.5.0",
        "executable": "crawl",
        "arguments": [
            "--url",
            "https://records.city.example/public-notice",
            "--workers",
            "1",
        ],
        "container": {
            "privileged": False,
            "host_network": False,
            "read_only_root": True,
            "shell": False,
            "cpu_limit": 1.0,
            "memory_limit_mb": 1024,
            "process_limit": 128,
            "mounts": [
                {
                    "source": "private://case-a/production-capture",
                    "target": "/crawls",
                }
            ],
        },
        "retry_policy": {"automatic_retry": False, "max_attempts": 1},
        "prepared_request": {
            "case_id": "case-a",
            "resource_limits": _limits(max_pages=2, max_download_bytes=2_000_000),
        },
    }
    plan.update(overrides)
    return plan


def _deployment_policy(**overrides) -> dict:
    value = {
        "runtime_enabled": True,
        "operator_confirmed": True,
        "execution_mode": "production",
        "deployment_id": "deployment-a",
        "execution_plan_sha256": PLAN_HASH,
        "execution_requested_at": "2026-07-21T20:15:00Z",
        "actor": "production-operator",
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


def _issue_payload(**overrides) -> dict:
    value = {
        "actor": "release-reviewer",
        "certification_plan": _certification_plan(),
        "certification_result": _certification_result(),
        "production_execution_plan": _production_execution_plan(),
        "deployment_policy": _deployment_policy(),
        "deployment_id": "deployment-a",
        "issued_at": "2026-07-21T20:00:00Z",
        "valid_from": "2026-07-21T20:05:00Z",
        "expires_at": "2026-07-22T08:05:00Z",
        "reason": "Authorize one certification-bound production capture.",
        "confirmed": True,
    }
    value.update(overrides)
    return value


def _configure_issue(monkeypatch) -> None:
    monkeypatch.setattr(service, "find_enablement", lambda value: None)
    monkeypatch.setattr(
        service,
        "_record",
        lambda action, actor, target, event, ip_address: {
            **event,
            "actor": actor,
            "audit_record_id": 1,
            "recorded_at": "2026-07-21T20:00:01+00:00",
        },
    )


def _issued(monkeypatch) -> dict:
    _configure_issue(monkeypatch)
    return service.issue_production_enablement(**_issue_payload())


def _claimed(monkeypatch) -> tuple[dict, dict]:
    issued = _issued(monkeypatch)
    active = {**issued, "enablement_state": "active"}
    monkeypatch.setattr(service, "find_enablement", lambda value: active)
    claim = service.claim_production_enablement(
        actor="production-operator",
        production_enablement_id=issued["production_enablement_id"],
        production_enablement_sha256=issued["production_enablement_sha256"],
        production_execution_plan=_production_execution_plan(),
        claimed_at="2026-07-21T20:10:00Z",
        reason="Claim the single production execution.",
        confirmed=True,
    )
    return issued, claim


def test_issues_time_bounded_single_use_scope(monkeypatch) -> None:
    issued = _issued(monkeypatch)
    assert issued["status"] == "browsertrix_production_enablement_issued"
    assert issued["production_enablement_granted"] is True
    assert issued["production_execution_authorized"] is False
    definition = issued["definition"]
    assert definition["single_use"] is True
    assert definition["automatic_execution"] is False
    assert definition["automatic_retry"] is False
    assert definition["authorized_scope"]["case_id"] == "case-a"
    assert definition["authorized_scope"]["approved_domain"] == (
        "records.city.example"
    )
    assert len(issued["production_enablement_sha256"]) == 64


def test_blocks_broader_resources_and_long_windows(monkeypatch) -> None:
    _configure_issue(monkeypatch)
    broad = _production_execution_plan()
    broad["prepared_request"] = {
        **broad["prepared_request"],
        "resource_limits": _limits(max_pages=6),
    }
    result = service.issue_production_enablement(
        **_issue_payload(production_execution_plan=broad)
    )
    assert result["blockers"] == [
        {"key": "production_resource_limits_exceed_certification"}
    ]

    result = service.issue_production_enablement(
        **_issue_payload(expires_at="2026-07-23T20:05:00Z")
    )
    assert result["blockers"] == [{"key": "enablement_window_invalid"}]


def test_claims_exact_plan_once_and_creates_runtime_authorization(monkeypatch) -> None:
    issued, claim = _claimed(monkeypatch)
    assert claim["status"] == "browsertrix_production_execution_authorized"
    assert claim["production_enablement_id"] == issued["production_enablement_id"]
    assert claim["production_execution_authorized"] is True
    authorization = claim["runtime_authorization"]
    assert authorization["single_use"] is True
    assert authorization["production_execution_plan_sha256"] == PLAN_HASH
    assert len(claim["runtime_authorization_sha256"]) == 64

    monkeypatch.setattr(
        service,
        "find_enablement",
        lambda value: {**issued, "enablement_state": "claimed"},
    )
    replay = service.claim_production_enablement(
        actor="production-operator",
        production_enablement_id=issued["production_enablement_id"],
        production_enablement_sha256=issued["production_enablement_sha256"],
        production_execution_plan=_production_execution_plan(),
        claimed_at="2026-07-21T20:11:00Z",
        reason="Attempt replay.",
        confirmed=True,
    )
    assert replay["blockers"] == [
        {"key": "active_unclaimed_production_enablement_required"}
    ]


def test_revoke_blocks_future_runtime_use(monkeypatch) -> None:
    issued, claim = _claimed(monkeypatch)
    claimed_state = {
        **issued,
        "enablement_state": "claimed",
        "claim_event": claim,
    }
    monkeypatch.setattr(service, "find_enablement", lambda value: claimed_state)
    revoked = service.revoke_production_enablement(
        actor="release-reviewer",
        production_enablement_id=issued["production_enablement_id"],
        production_enablement_sha256=issued["production_enablement_sha256"],
        revoked_at="2026-07-21T20:12:00Z",
        reason="Emergency stop.",
        confirmed=True,
    )
    assert revoked["status"] == "browsertrix_production_enablement_revoked"
    assert revoked["production_enablement_granted"] is False


def _storage_resolver(uri: str) -> runtime.ResolvedStorageTarget:
    return runtime.ResolvedStorageTarget(
        logical_uri=uri,
        host_path="/srv/socmint/browsertrix/case-a/production-capture",
        approved_root="/srv/socmint/browsertrix",
        created_empty=True,
        symlink_safe=True,
        restrictive_permissions=True,
    )


def _runtime_inspector(runtime_name: str, image_reference: str):
    return runtime.RuntimeInspection(
        runtime=runtime_name,
        binary_path="/usr/bin/docker",
        runtime_version="Docker test",
        image_reference=image_reference,
        local_image_digest=DIGEST,
        image_present_locally=True,
    )


def test_production_runtime_requires_persisted_claim(monkeypatch) -> None:
    issued, claim = _claimed(monkeypatch)
    validation = service.validate_runtime_authorization(
        runtime_authorization=claim,
        execution_plan=_production_execution_plan(),
        deployment_policy=_deployment_policy(),
    )
    assert validation["status"] == "production_runtime_authorization_validated"

    monkeypatch.setattr(
        runtime,
        "validate_runtime_authorization",
        lambda **kwargs: validation,
    )
    monkeypatch.setattr(
        runtime,
        "find_enablement",
        lambda value: {
            **issued,
            "enablement_state": "claimed",
            "claim_event": claim,
        },
    )
    prepared = runtime.prepare_container_runtime(
        execution_plan=_production_execution_plan(),
        deployment_policy=_deployment_policy(),
        production_authorization=claim,
        storage_resolver=_storage_resolver,
        runtime_inspector=_runtime_inspector,
    )
    assert prepared["status"] == "browsertrix_container_runtime_prepared"
    assert prepared["execution_mode"] == "production"
    assert prepared["production_authorization"] == {
        "production_enablement_id": issued["production_enablement_id"],
        "production_enablement_sha256": issued["production_enablement_sha256"],
        "runtime_authorization_sha256": claim["runtime_authorization_sha256"],
    }

    monkeypatch.setattr(
        runtime,
        "find_enablement",
        lambda value: {**issued, "enablement_state": "revoked"},
    )
    blocked = runtime.prepare_container_runtime(
        execution_plan=_production_execution_plan(),
        deployment_policy=_deployment_policy(),
        production_authorization=claim,
        storage_resolver=_storage_resolver,
        runtime_inspector=_runtime_inspector,
    )
    assert blocked["blockers"] == [
        {"key": "current_claimed_production_enablement_required"}
    ]


def test_v35_ledger_prevents_duplicate_production_execution(monkeypatch) -> None:
    issued, claim = _claimed(monkeypatch)
    validation = service.validate_runtime_authorization(
        runtime_authorization=claim,
        execution_plan=_production_execution_plan(),
        deployment_policy=_deployment_policy(),
    )
    monkeypatch.setattr(runtime, "validate_runtime_authorization", lambda **kwargs: validation)
    monkeypatch.setattr(
        runtime,
        "find_enablement",
        lambda value: {
            **issued,
            "enablement_state": "claimed",
            "claim_event": claim,
        },
    )
    prepared = runtime.prepare_container_runtime(
        execution_plan=_production_execution_plan(),
        deployment_policy=_deployment_policy(),
        production_authorization=claim,
        storage_resolver=_storage_resolver,
        runtime_inspector=_runtime_inspector,
    )

    ledger_calls = []

    def create_execution(**kwargs):
        ledger_calls.append(("create", kwargs))
        return {
            "created": True,
            "execution_id": "durable-execution-a",
            "state": "pending",
            "state_version": 0,
        }

    def transition_execution(**kwargs):
        ledger_calls.append(("transition", kwargs))
        version = 1 if kwargs["new_state"] == "running" else 2
        return {
            "execution_id": kwargs["execution_id"],
            "state": kwargs["new_state"],
            "state_version": version,
        }

    monkeypatch.setattr(runtime, "create_execution", create_execution)
    monkeypatch.setattr(runtime, "transition_execution", transition_execution)

    result = runtime.execute_container_runtime(
        runtime_request=prepared,
        process_runner=lambda command, timeout: runtime.ProcessOutcome(
            exit_code=0,
            stdout="completed",
            stderr="",
        ),
        result_loader=lambda plan, storage, outcome: ExecutionResult(
            exit_code=0,
            stdout="completed",
            stderr="",
            timed_out=False,
            cancelled=False,
            started_at="2026-07-21T20:15:00Z",
            completed_at="2026-07-21T20:16:00Z",
            browsertrix_version="1.5.0",
            browser_version="fictional-browser",
            final_url="https://records.city.example/public-notice",
            redirect_chain=[],
            page_count=1,
            downloaded_bytes=100,
            outputs=[],
        ),
    )
    assert result["status"] == "browsertrix_container_execution_completed"
    assert result["execution_state"] == "succeeded"
    assert result["durable_replay_protection"] is True
    assert [item[0] for item in ledger_calls] == [
        "create",
        "transition",
        "transition",
    ]

    monkeypatch.setattr(
        runtime,
        "create_execution",
        lambda **kwargs: {
            "created": False,
            "execution_id": "durable-execution-a",
            "state": "succeeded",
        },
    )
    replay_calls = []
    replay = runtime.execute_container_runtime(
        runtime_request=prepared,
        process_runner=lambda command, timeout: replay_calls.append(command),
        result_loader=lambda *args: None,
    )
    assert replay["blockers"] == [
        {"key": "production_runtime_authorization_already_consumed"}
    ]
    assert replay_calls == []
