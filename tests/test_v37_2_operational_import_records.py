from src.socmint import operational_import_records_v37_2 as service


IMPORT = {
    "operational_import_id": "import-a",
    "operational_import_event_sha256": "a" * 64,
    "envelope_sha256": "b" * 64,
    "rerun_key_sha256": "c" * 64,
}


def _record(**overrides):
    value = {
        "source_record_id": "record-1",
        "record_type": "entity_reference",
        "raw_value": "Entity Alpha",
        "normalized_value": "entity alpha",
        "observed_at": "2026-07-20T01:00:00Z",
        "extraction_confidence": 0.9,
        "context": {"synthetic_fixture": True},
        "source_references": ["fixture://record-1"],
        "warnings": [],
    }
    value.update(overrides)
    return value


def _configure(monkeypatch, *, batches=None, records=None, existing_batch=None):
    monkeypatch.setattr(service, "find_import", lambda import_id: IMPORT)
    monkeypatch.setattr(service, "current_batches", lambda: batches or [])
    monkeypatch.setattr(service, "current_staged_records", lambda import_id=None: records or [])
    monkeypatch.setattr(service, "find_batch", lambda batch_id: existing_batch)
    monkeypatch.setattr(
        service,
        "_record",
        lambda actor, batch_id, event, ip_address: {
            **event,
            "actor": actor,
            "audit_record_id": 1,
            "recorded_at": "2026-07-20T01:02:00+00:00",
        },
    )


def _stage(monkeypatch, submitted_records, **overrides):
    _configure(monkeypatch, **overrides)
    return service.stage_import_records(
        actor="admin",
        import_id="import-a",
        records=submitted_records,
        adapter_diagnostics={
            "schema": "socmint.import_adapter_result.v37_2",
            "network_access_performed": False,
            "collection_performed": False,
            "payload_persisted": False,
        },
        reason="Stage fictional records for review.",
        confirmed=True,
    )


def test_v37_2_stages_accepted_and_quarantined_records(monkeypatch):
    result = _stage(
        monkeypatch,
        [
            _record(),
            _record(
                source_record_id="record-2",
                raw_value="Entity Beta",
                normalized_value="entity beta",
                extraction_confidence=0.4,
                warnings=["low_quality_source_field"],
            ),
        ],
    )
    assert result["status"] == "import_records_staged"
    assert result["record_counts"] == {
        "submitted": 2,
        "staged": 2,
        "accepted": 1,
        "quarantined": 1,
        "duplicate": 0,
        "rejected": 0,
    }
    states = [item["initial_state"] for item in result["records"]]
    assert states == ["accepted", "quarantined"]
    assert result["records"][0]["claim_support_allowed"] is True
    assert result["records"][1]["claim_support_allowed"] is False
    assert result["raw_export_payload_recorded"] is False
    assert result["observation_created"] is False


def test_v37_2_detects_duplicate_within_batch(monkeypatch):
    record = _record()
    result = _stage(monkeypatch, [record, dict(record)])
    assert result["record_counts"]["accepted"] == 1
    assert result["record_counts"]["duplicate"] == 1
    duplicate = result["records"][1]
    assert duplicate["initial_state"] == "duplicate"
    assert duplicate["duplicate_of_staged_record_id"]
    assert duplicate["claim_support_allowed"] is False


def test_v37_2_detects_duplicate_across_import_history(monkeypatch):
    normalized = service._normalize_record("import-a", _record())
    assert normalized is not None
    result = _stage(monkeypatch, [_record()], records=[normalized])
    assert result["record_counts"]["duplicate"] == 1
    assert result["records"][0]["duplicate_of_staged_record_id"] == normalized[
        "staged_record_id"
    ]


def test_v37_2_reuses_identical_batch(monkeypatch):
    existing = {
        "staged_record_batch_id": "batch-existing",
        "operational_import_id": "import-a",
    }
    result = _stage(monkeypatch, [_record()], existing_batch=existing)
    assert result["status"] == "staged_record_batch_reused"
    assert result["idempotent_replay"] is True


def test_v37_2_blocks_invalid_or_networked_adapter_output(monkeypatch):
    _configure(monkeypatch)
    result = service.stage_import_records(
        actor="admin",
        import_id="import-a",
        records=[{"bad": "record"}],
        adapter_diagnostics={},
        reason="Test.",
        confirmed=True,
    )
    assert result["blockers"] == [{"key": "import_record_contract_invalid"}]

    result = service.stage_import_records(
        actor="admin",
        import_id="import-a",
        records=[_record()],
        adapter_diagnostics={"network_access_performed": True},
        reason="Test.",
        confirmed=True,
    )
    assert result["blockers"] == [{"key": "networked_adapter_output_not_allowed"}]


def test_v37_2_requires_confirmation_and_batch_limit(monkeypatch):
    _configure(monkeypatch)
    result = service.stage_import_records(
        actor="admin",
        import_id="import-a",
        records=[_record()],
        adapter_diagnostics={},
        reason="Test.",
        confirmed=False,
    )
    assert result["blockers"] == [
        {"key": "explicit_record_staging_confirmation_required"}
    ]
    result = service.stage_import_records(
        actor="admin",
        import_id="import-a",
        records=[_record()] * (service.MAX_BATCH_RECORDS + 1),
        adapter_diagnostics={},
        reason="Test.",
        confirmed=True,
    )
    assert result["blockers"] == [{"key": "import_record_batch_limit_exceeded"}]
