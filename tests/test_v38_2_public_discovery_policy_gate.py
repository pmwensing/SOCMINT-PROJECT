from src.socmint import public_discovery_policy_gate_v38_2 as service


def _request(**overrides):
    request = {
        "discovery_request_id": "public-discovery-request-a",
        "discovery_request_event_sha256": "a" * 64,
        "manifest_sha256": "b" * 64,
        "manifest": {
            "case_id": "case-a",
            "collection_job_binding": {"collection_job_id": "collection-job-a"},
            "policy_evaluation_binding": {
                "policy_evaluation_id": "collection-policy-evaluation-a"
            },
            "query_terms": ["fictional order number", "46 Example Street"],
            "seed_urls": ["https://example.test/notices"],
            "resource_limits": {
                "allowed_domains": ["example.test"],
                "max_pages": 20,
                "max_depth": 2,
                "delay_seconds": 2.0,
                "concurrent_requests_per_domain": 1,
                "max_redirects": 4,
                "max_response_bytes": 5_000_000,
                "allowed_content_types": ["application/pdf", "text/html"],
            },
        },
    }
    request.update(overrides)
    return request


def _policy_limits(**overrides):
    limits = {
        "allowed_domains": ["example.test"],
        "max_pages": 100,
        "max_depth": 2,
        "min_delay_seconds": 2,
        "max_concurrent_requests_per_domain": 1,
        "max_redirects": 5,
        "max_response_bytes": 10_000_000,
        "allowed_content_types": ["application/pdf", "text/html"],
    }
    limits.update(overrides)
    return limits


def _payload(**overrides):
    payload = {
        "actor": "admin",
        "discovery_request_id": "public-discovery-request-a",
        "source_tier": "tier_1_official",
        "allowlisted_domains": ["example.test"],
        "direct_case_relevance": True,
        "candidate_entity_reviewed": False,
        "public_access_confirmed": True,
        "robots_decision": "allow",
        "terms_decision": "reviewed_allow",
        "access_indicators": {
            "login_required": False,
            "paywall_required": False,
            "captcha_required": False,
            "private_account": False,
        },
        "policy_limits": _policy_limits(),
        "reason": "Evaluate the fictional public discovery request.",
        "confirmed": True,
    }
    payload.update(overrides)
    return payload


def _configure(monkeypatch, *, request=None, existing=None):
    monkeypatch.setattr(
        service,
        "find_discovery_request",
        lambda discovery_request_id: request,
    )
    monkeypatch.setattr(service, "find_gate_decision", lambda gate_id: existing)
    monkeypatch.setattr(
        service,
        "_record",
        lambda actor, gate_id, event, ip_address: {
            **event,
            "actor": actor,
            "audit_record_id": 1,
            "recorded_at": "2026-07-21T08:00:00+00:00",
        },
    )


def test_v38_2_allows_scoped_public_request_without_execution(monkeypatch):
    _configure(monkeypatch, request=_request())
    result = service.evaluate_discovery_request(**_payload())

    assert result["status"] == "public_discovery_policy_gate_evaluated"
    assert result["decision"] == "allow"
    assert result["decision_blockers"] == []
    assert result["passive_discovery_eligible"] is True
    assert result["live_network_eligible"] is False
    assert result["network_request_performed"] is False
    assert result["archive_query_performed"] is False
    assert result["crawler_execution_performed"] is False
    assert result["browser_capture_performed"] is False
    assert result["artifact_created"] is False
    assert result["source_registered"] is False
    assert result["observation_created"] is False


def test_v38_2_records_block_decision_for_scope_and_query_violations(monkeypatch):
    manifest = {
        **_request()["manifest"],
        "query_terms": ["71 Cowdy Street credential dump"],
    }
    _configure(monkeypatch, request=_request(manifest=manifest))
    result = service.evaluate_discovery_request(
        **_payload(direct_case_relevance=False, candidate_entity_reviewed=False)
    )

    assert result["decision"] == "block"
    assert result["passive_discovery_eligible"] is False
    assert "direct_relevance_or_reviewed_candidate_required" in result[
        "decision_blockers"
    ]
    assert "excluded_address_query_blocked" in result["decision_blockers"]
    assert "prohibited_query_intent_blocked" in result["decision_blockers"]


def test_v38_2_blocks_robots_terms_and_nonpublic_access(monkeypatch):
    _configure(monkeypatch, request=_request())
    result = service.evaluate_discovery_request(
        **_payload(
            public_access_confirmed=False,
            robots_decision="disallow",
            terms_decision="reviewed_block",
            access_indicators={
                "login_required": True,
                "paywall_required": True,
                "captcha_required": True,
                "private_account": True,
            },
        )
    )

    assert result["decision"] == "block"
    assert "public_access_required" in result["decision_blockers"]
    assert "robots_allow_required" in result["decision_blockers"]
    assert "terms_review_allow_required" in result["decision_blockers"]
    assert "login_required_blocked" in result["decision_blockers"]
    assert "paywall_required_blocked" in result["decision_blockers"]
    assert "captcha_required_blocked" in result["decision_blockers"]
    assert "private_account_blocked" in result["decision_blockers"]


def test_v38_2_enforces_allowlist_and_resource_ceiling(monkeypatch):
    _configure(monkeypatch, request=_request())
    result = service.evaluate_discovery_request(
        **_payload(
            allowlisted_domains=["other.test"],
            policy_limits=_policy_limits(
                allowed_domains=["other.test"],
                max_pages=5,
                min_delay_seconds=5,
            ),
        )
    )

    assert result["decision"] == "block"
    assert "request_domain_not_source_allowlisted" in result["decision_blockers"]
    assert "seed_url_not_source_allowlisted" in result["decision_blockers"]
    assert "requested_domain_outside_policy_allowlist" in result[
        "decision_blockers"
    ]
    assert "requested_page_limit_exceeds_policy" in result["decision_blockers"]
    assert "requested_delay_below_policy_minimum" in result["decision_blockers"]


def test_v38_2_reuses_identical_gate_decision(monkeypatch):
    _configure(monkeypatch, request=_request())
    first = service.evaluate_discovery_request(**_payload())
    _configure(monkeypatch, request=_request(), existing=first)
    replay = service.evaluate_discovery_request(**_payload())

    assert replay["status"] == "public_discovery_policy_gate_reused"
    assert replay["idempotent_replay"] is True
    assert replay["next_action"] == "stage_offline_passive_discovery"


def test_v38_2_requires_structured_inputs_and_confirmation(monkeypatch):
    _configure(monkeypatch, request=_request())

    result = service.evaluate_discovery_request(
        **_payload(access_indicators={"login_required": False})
    )
    assert result["blockers"] == [{"key": "access_indicators_incomplete"}]

    result = service.evaluate_discovery_request(
        **_payload(policy_limits={"max_pages": 1})
    )
    assert result["blockers"] == [{"key": "policy_limits_incomplete"}]

    result = service.evaluate_discovery_request(**_payload(confirmed=False))
    assert result["blockers"] == [
        {"key": "explicit_discovery_gate_confirmation_required"}
    ]
