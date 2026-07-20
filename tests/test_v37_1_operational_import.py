from src.socmint import operational_import_v37_1 as service


HASH = "a" * 64


def _artifact(*, state="accepted", case_id="case-a", content_hash=HASH):
    return {
        "artifact_id": "artifact-a",
        "artifact_state": state,
        "content_sha256": content_hash,
        "acquisition_sha256": "b" * 64,
        "collection_job_id": "job-a",
        "contract_binding": {
            "case_id": case_id,
            "entity_id": "entity-a",
            "source_id": "source-seed-a",
        },
        "artifact_event_sha256": "c" * 64,
        "state_history": [
            {
                "artifact_event_sha256": "d" * 64,
            }
        ],
    }


def _payload(**overrides):
    payload = {
        "actor": "admin",
        "case_id": "case-a",
        "purpose": "Import an operator-provided fictional tool export.",
        "artifact_id": "artifact-a",
        "content_sha256": HASH,
        "original_filename": "fictional-export.json",
        "media_type": "application/json",
        "export_format": "json",
        "tool_name": "FictionalTool",
        "tool_version": "1.0",
        "adapter_name": "fictional-json",
        "adapter_version": "1.0",
        "exported_at": "2026-07-20T01:00:00Z",
        "imported_at": "2026-07-20T01:10:00Z",
        "declared_record_count": 3,
        "source_references": ["https://example.test/source"],
        "collection_context": {"operator_export": True, "synthetic_fixture": True},
        "reason": "Register the import envelope for review.",
        "confirmed": True,
    }
    payload.update(overrides)
    return payload


def _configure(monkeypatch, *, artifact=None, existing=None):
    monkeypatch.setattr(service, "find_artifact", lambda artifact_id: artifact)
    monkeypatch.setattr(service, "find_import", lambda import_id: existing)
    monkeypatch.setattr(
        service,
        "_record",
        lambda actor, import_id, event, ip_address: {
            **event,
            "actor": actor,
            "audit_record_id": 1,
            "recorded_at": "2026-07-20T01:10:01+00:00",
        },
    )


def test_v37_1_registers_hash_bound_case_scoped_import(monkeypatch):
    _configure(monkeypatch, artifact=_artifact())
    result = service.register_import_envelope(**_payload())
    assert result["status"] == "operational_import_registered"
    assert result["envelope"]["case_id"] == "case-a"
    assert result["envelope"]["artifact_binding"]["artifact_id"] == "artifact-a"
    assert result["envelope"]["original_filename"] == "fictional-export.json"
    assert result["envelope"]["tool"] == {"name": "FictionalTool", "version": "1.0"}
    assert result["envelope"]["adapter"] == {
        "name": "fictional-json",
        "version": "1.0",
    }
    assert result["record_counts"]["declared"] == 3
    assert result["raw_payload_recorded"] is False
    assert result["connector_execution_performed"] is False
    assert result["hidden_collection_performed"] is False
    assert result["observation_created"] is False
    assert result["export_created"] is False
    assert result["published"] is False


def test_v37_1_reuses_deterministic_import_instead_of_duplicating(monkeypatch):
    existing = {
        "schema": service.SCHEMA,
        "version": service.VERSION,
        "operational_import_id": "operational-import-existing",
        "envelope": {"case_id": "case-a"},
    }
    _configure(monkeypatch, artifact=_artifact(), existing=existing)
    result = service.register_import_envelope(**_payload())
    assert result["status"] == "operational_import_reused"
    assert result["idempotent_replay"] is True
    assert result["next_action"] == "stage_import_records"


def test_v37_1_blocks_unaccepted_artifact_and_case_or_hash_mismatch(monkeypatch):
    _configure(monkeypatch, artifact=_artifact(state="quarantined"))
    result = service.register_import_envelope(**_payload())
    assert result["blockers"] == [{"key": "accepted_evidence_artifact_required"}]

    _configure(monkeypatch, artifact=_artifact(case_id="other-case"))
    result = service.register_import_envelope(**_payload())
    assert result["blockers"] == [{"key": "import_case_artifact_binding_mismatch"}]

    _configure(monkeypatch, artifact=_artifact(content_hash="e" * 64))
    result = service.register_import_envelope(**_payload())
    assert result["blockers"] == [{"key": "import_content_artifact_hash_mismatch"}]


def test_v37_1_blocks_paths_bad_formats_and_reversed_times(monkeypatch):
    _configure(monkeypatch, artifact=_artifact())
    assert service.register_import_envelope(
        **_payload(original_filename="../secret.json")
    )["blockers"] == [{"key": "original_filename_invalid"}]
    assert service.register_import_envelope(
        **_payload(export_format="xlsx")
    )["blockers"] == [{"key": "export_format_invalid"}]
    assert service.register_import_envelope(
        **_payload(
            exported_at="2026-07-20T02:00:00Z",
            imported_at="2026-07-20T01:00:00Z",
        )
    )["blockers"] == [{"key": "import_time_precedes_export_time"}]


def test_v37_1_requires_explicit_confirmation_and_metadata(monkeypatch):
    _configure(monkeypatch, artifact=_artifact())
    assert service.register_import_envelope(
        **_payload(confirmed=False)
    )["blockers"] == [{"key": "explicit_import_confirmation_required"}]
    assert service.register_import_envelope(
        **_payload(collection_context=None)
    )["blockers"] == [{"key": "collection_context_object_required"}]
    assert service.register_import_envelope(
        **_payload(declared_record_count=-1)
    )["blockers"] == [{"key": "declared_record_count_invalid"}]
