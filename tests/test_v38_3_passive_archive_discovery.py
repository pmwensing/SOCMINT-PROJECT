from src.socmint import passive_archive_discovery_v38_3 as service


def _gate(**overrides):
    gate = {
        "gate_decision_id": "public-discovery-gate-a",
        "gate_decision_event_sha256": "a" * 64,
        "discovery_request_id": "public-discovery-request-a",
        "request_binding_sha256": "b" * 64,
        "evaluation_sha256": "c" * 64,
        "decision": "allow",
        "passive_discovery_eligible": True,
        "live_network_eligible": False,
    }
    gate.update(overrides)
    return gate


def _common_crawl_records():
    return [
        {
            "url": "https://example.test/notices/1",
            "timestamp": "20260720010000",
            "digest": "sha1:fictional-a",
            "status": "200",
            "mime": "text/html",
            "filename": "crawl-data/fictional-a.warc.gz",
        },
        {
            "url": "https://example.test/notices/1",
            "timestamp": "20260720010000",
            "digest": "sha1:fictional-a",
            "status": "200",
            "mime": "text/html",
            "filename": "crawl-data/fictional-a.warc.gz",
        },
        {
            "url": "not-a-url",
            "timestamp": "bad-time",
            "digest": "",
        },
    ]


def _payload(**overrides):
    payload = {
        "actor": "admin",
        "gate_decision_id": "public-discovery-gate-a",
        "provider": "common_crawl",
        "index_version": "CC-MAIN-FICTIONAL",
        "query_reference": "fictional-query-a",
        "queried_at": "2026-07-21T09:00:00Z",
        "adapter_name": "common-crawl-offline-fixture",
        "adapter_version": "1.0",
        "response_records": _common_crawl_records(),
        "reason": "Stage operator-provided fictional index responses.",
        "confirmed": True,
    }
    payload.update(overrides)
    return payload


def _configure(monkeypatch, *, gate=None, existing_batch=None, existing_keys=None):
    monkeypatch.setattr(service, "find_gate_decision", lambda gate_id: gate)
    monkeypatch.setattr(
        service,
        "find_passive_batch",
        lambda batch_id: existing_batch,
    )
    monkeypatch.setattr(
        service,
        "_existing_candidate_keys",
        lambda: set(existing_keys or []),
    )
    monkeypatch.setattr(
        service,
        "_record",
        lambda actor, batch_id, event, ip_address: {
            **event,
            "actor": actor,
            "audit_record_id": 1,
            "recorded_at": "2026-07-21T09:00:01+00:00",
        },
    )


def test_v38_3_stages_offline_common_crawl_candidates(monkeypatch):
    _configure(monkeypatch, gate=_gate())
    result = service.register_passive_discovery_batch(**_payload())

    assert result["status"] == "passive_archive_discovery_batch_registered"
    assert result["provider"] == "common_crawl"
    assert result["counts"] == {
        "input": 3,
        "accepted": 1,
        "duplicate": 1,
        "quarantined": 1,
    }
    assert result["candidates"][0]["candidate_url"] == (
        "https://example.test/notices/1"
    )
    assert result["candidates"][0]["record_status"] == "accepted"
    assert result["candidates"][1]["record_status"] == "duplicate"
    assert result["candidates"][2]["record_status"] == "quarantined"
    assert result["raw_response_recorded"] is False
    assert result["offline_response_consumed"] is True
    assert result["network_request_performed"] is False
    assert result["archive_query_performed"] is False
    assert result["artifact_created"] is False
    assert result["source_registered"] is False
    assert result["observation_created"] is False


def test_v38_3_normalizes_internet_archive_fixture(monkeypatch):
    _configure(monkeypatch, gate=_gate())
    result = service.register_passive_discovery_batch(
        **_payload(
            provider="internet_archive",
            index_version="CDX-FICTIONAL",
            adapter_name="internet-archive-offline-fixture",
            response_records=[
                {
                    "original": "https://example.test/public/order.pdf",
                    "timestamp": "20260719083000",
                    "digest": "fictional-digest-b",
                    "statuscode": "200",
                    "mimetype": "application/pdf",
                    "wayback_url": "https://web.archive.test/fictional",
                }
            ],
        )
    )

    assert result["counts"]["accepted"] == 1
    candidate = result["candidates"][0]
    assert candidate["provider"] == "internet_archive"
    assert candidate["candidate_url"] == "https://example.test/public/order.pdf"
    assert candidate["capture_timestamp"].startswith("2026-07-19T08:30:00")
    assert candidate["evidence_status"] == "candidate_only"
    assert candidate["review_required"] is True


def test_v38_3_requires_allowing_pre_live_network_gate(monkeypatch):
    _configure(monkeypatch, gate=_gate(decision="block", passive_discovery_eligible=False))
    result = service.register_passive_discovery_batch(**_payload())
    assert result["blockers"] == [
        {"key": "allowing_passive_discovery_gate_required"}
    ]

    _configure(monkeypatch, gate=_gate(live_network_eligible=True))
    result = service.register_passive_discovery_batch(**_payload())
    assert result["blockers"] == [{"key": "pre_live_network_gate_state_required"}]


def test_v38_3_detects_duplicates_across_batches(monkeypatch):
    first_candidate = service._normalize_record(
        "common_crawl", _common_crawl_records()[0]
    )
    _configure(
        monkeypatch,
        gate=_gate(),
        existing_keys=[first_candidate["duplicate_key_sha256"]],
    )
    result = service.register_passive_discovery_batch(
        **_payload(response_records=[_common_crawl_records()[0]])
    )
    assert result["counts"]["duplicate"] == 1
    assert result["counts"]["accepted"] == 0


def test_v38_3_reuses_deterministic_batch(monkeypatch):
    _configure(monkeypatch, gate=_gate())
    first = service.register_passive_discovery_batch(**_payload())
    _configure(monkeypatch, gate=_gate(), existing_batch=first)
    replay = service.register_passive_discovery_batch(**_payload())

    assert replay["status"] == "passive_archive_discovery_batch_reused"
    assert replay["idempotent_replay"] is True


def test_v38_3_requires_offline_records_and_explicit_confirmation(monkeypatch):
    _configure(monkeypatch, gate=_gate())

    result = service.register_passive_discovery_batch(
        **_payload(response_records=[])
    )
    assert result["blockers"] == [{"key": "offline_response_records_required"}]

    result = service.register_passive_discovery_batch(**_payload(confirmed=False))
    assert result["blockers"] == [
        {"key": "explicit_passive_discovery_confirmation_required"}
    ]
