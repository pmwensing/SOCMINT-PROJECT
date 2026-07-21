from src.socmint import public_discovery_request_v38_1 as service


def _contract(**overrides):
    contract = {
        "collection_job_id": "collection-job-a",
        "collection_job_event_sha256": "a" * 64,
        "definition_sha256": "b" * 64,
        "current_state": "drafted",
        "attempt_number": 1,
        "case_id": "case-a",
        "entity_id": "entity-a",
        "source_id": "source-a",
        "purpose": "Discover public records for the fictional case.",
        "connector": "official_public_web",
    }
    contract.update(overrides)
    return contract


def _evaluation(**overrides):
    evaluation = {
        "event_type": "collection_policy_evaluated",
        "collection_job_id": "collection-job-a",
        "policy_evaluation_id": "collection-policy-evaluation-a",
        "policy_event_sha256": "c" * 64,
        "evaluation_sha256": "d" * 64,
        "contract_binding": {
            "collection_job_id": "collection-job-a",
            "contract_event_sha256": "a" * 64,
        },
        "evaluation": {
            "decision": "allow",
            "allowed_by_policy_ids": ["collection-policy-a"],
            "denied_by_policy_ids": [],
            "jurisdiction": "CA-ON",
        },
    }
    evaluation.update(overrides)
    return evaluation


def _limits(**overrides):
    limits = {
        "allowed_domains": ["example.test"],
        "max_pages": 20,
        "max_depth": 2,
        "delay_seconds": 2,
        "concurrent_requests_per_domain": 1,
        "max_redirects": 4,
        "max_response_bytes": 5_000_000,
        "allowed_content_types": ["text/html", "application/pdf"],
    }
    limits.update(overrides)
    return limits


def _payload(**overrides):
    payload = {
        "actor": "admin",
        "case_id": "case-a",
        "purpose": "Discover public records for the fictional case.",
        "collection_job_id": "collection-job-a",
        "policy_evaluation_id": "collection-policy-evaluation-a",
        "source_class": "official_public_web",
        "adapter_intent": "common_crawl_index",
        "jurisdiction": "CA-ON",
        "query_terms": ["fictional order number", "46 Example Street"],
        "seed_urls": ["https://example.test/notices"],
        "resource_limits": _limits(),
        "idempotency_key": "fictional-discovery-request-a",
        "reason": "Register the discovery request before policy review.",
        "confirmed": True,
    }
    payload.update(overrides)
    return payload


def _configure(monkeypatch, *, contract=None, evaluations=None, existing=None):
    monkeypatch.setattr(service, "find_contract", lambda job_id: contract)
    monkeypatch.setattr(service, "policy_history", lambda: evaluations or [])
    monkeypatch.setattr(
        service,
        "_find_by_idempotency_key",
        lambda idempotency_key: existing,
    )
    monkeypatch.setattr(
        service,
        "_record",
        lambda actor, request_id, event, ip_address: {
            **event,
            "actor": actor,
            "audit_record_id": 1,
            "recorded_at": "2026-07-21T07:00:00+00:00",
        },
    )


def test_v38_1_registers_hash_bound_nonexecuting_discovery_request(monkeypatch):
    _configure(monkeypatch, contract=_contract(), evaluations=[_evaluation()])
    result = service.register_discovery_request(**_payload())

    assert result["status"] == "public_discovery_request_registered"
    assert result["manifest"]["case_id"] == "case-a"
    assert result["manifest"]["collection_job_binding"]["collection_job_id"] == (
        "collection-job-a"
    )
    assert result["manifest"]["policy_evaluation_binding"]["decision"] == "allow"
    assert result["manifest"]["seed_urls"] == ["https://example.test/notices"]
    assert result["manifest"]["resource_limits"]["max_pages"] == 20
    assert result["execution_eligible"] is False
    assert result["network_request_performed"] is False
    assert result["dns_lookup_performed"] is False
    assert result["archive_query_performed"] is False
    assert result["crawler_execution_performed"] is False
    assert result["browser_capture_performed"] is False
    assert result["artifact_created"] is False
    assert result["source_registered"] is False
    assert result["observation_created"] is False
    assert result["published"] is False


def test_v38_1_is_idempotent_and_blocks_conflicting_reuse(monkeypatch):
    _configure(monkeypatch, contract=_contract(), evaluations=[_evaluation()])
    first = service.register_discovery_request(**_payload())
    existing = {
        **first,
        "definition_sha256": first["definition_sha256"],
    }
    _configure(
        monkeypatch,
        contract=_contract(),
        evaluations=[_evaluation()],
        existing=existing,
    )
    replay = service.register_discovery_request(**_payload())
    assert replay["status"] == "public_discovery_request_reused"
    assert replay["idempotent_replay"] is True

    conflict = service.register_discovery_request(
        **_payload(query_terms=["different fictional term"])
    )
    assert conflict["blockers"] == [{"key": "idempotency_key_conflict"}]


def test_v38_1_requires_allowing_current_policy_binding(monkeypatch):
    _configure(monkeypatch, contract=_contract(), evaluations=[])
    result = service.register_discovery_request(**_payload())
    assert result["blockers"] == [{"key": "collection_policy_evaluation_required"}]

    denied = _evaluation(evaluation={"decision": "deny", "jurisdiction": "CA-ON"})
    _configure(monkeypatch, contract=_contract(), evaluations=[denied])
    result = service.register_discovery_request(**_payload())
    assert result["blockers"] == [
        {"key": "allowing_collection_policy_evaluation_required"}
    ]

    mismatch = _evaluation(
        contract_binding={
            "collection_job_id": "collection-job-a",
            "contract_event_sha256": "e" * 64,
        }
    )
    _configure(monkeypatch, contract=_contract(), evaluations=[mismatch])
    result = service.register_discovery_request(**_payload())
    assert result["blockers"] == [
        {"key": "policy_evaluation_contract_binding_mismatch"}
    ]


def test_v38_1_blocks_job_scope_mismatch_and_terminal_jobs(monkeypatch):
    _configure(
        monkeypatch,
        contract=_contract(case_id="other-case"),
        evaluations=[_evaluation()],
    )
    result = service.register_discovery_request(**_payload())
    assert result["blockers"] == [
        {"key": "discovery_case_collection_job_mismatch"}
    ]

    _configure(
        monkeypatch,
        contract=_contract(current_state="completed"),
        evaluations=[_evaluation()],
    )
    result = service.register_discovery_request(**_payload())
    assert result["blockers"] == [{"key": "active_collection_job_required"}]


def test_v38_1_requires_explicit_limits_safe_seeds_and_confirmation(monkeypatch):
    _configure(monkeypatch, contract=_contract(), evaluations=[_evaluation()])

    result = service.register_discovery_request(
        **_payload(resource_limits={"max_pages": 1})
    )
    assert result["blockers"] == [{"key": "resource_limits_incomplete"}]

    result = service.register_discovery_request(
        **_payload(seed_urls=["https://user:pass@example.test/private"])
    )
    assert result["blockers"] == [{"key": "seed_url_invalid"}]

    result = service.register_discovery_request(
        **_payload(query_terms=[], seed_urls=[])
    )
    assert result["blockers"] == [{"key": "query_or_seed_required"}]

    result = service.register_discovery_request(**_payload(confirmed=False))
    assert result["blockers"] == [
        {"key": "explicit_discovery_request_confirmation_required"}
    ]
