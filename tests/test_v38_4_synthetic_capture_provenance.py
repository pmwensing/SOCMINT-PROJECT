from src.socmint import synthetic_capture_provenance_v38_4 as service


def _candidate(**overrides):
    candidate = {
        "candidate_id": "passive-archive-candidate-a",
        "candidate_sha256": "a" * 64,
        "candidate_url": "https://example.test/notices/1",
        "record_status": "accepted",
        "review_required": True,
    }
    candidate.update(overrides)
    return candidate


def _batch(**overrides):
    batch = {
        "passive_discovery_batch_id": "passive-archive-batch-a",
        "passive_discovery_event_sha256": "b" * 64,
        "gate_decision_id": "public-discovery-gate-a",
        "candidates": [_candidate()],
    }
    batch.update(overrides)
    return batch


def _gate(**overrides):
    gate = {
        "gate_decision_id": "public-discovery-gate-a",
        "gate_decision_event_sha256": "c" * 64,
        "discovery_request_id": "public-discovery-request-a",
        "decision": "allow",
        "live_network_eligible": False,
    }
    gate.update(overrides)
    return gate


def _request():
    return {
        "discovery_request_id": "public-discovery-request-a",
        "manifest": {
            "case_id": "case-a",
            "purpose": "Preserve fictional public records.",
            "collection_job_binding": {
                "collection_job_id": "collection-job-a",
                "attempt_number": 1,
            },
        },
    }


def _capture_files():
    return [
        {
            "role": "primary_html",
            "filename": "fictional-page.html",
            "media_type": "text/html",
            "content": "<html><body>Fictional public notice</body></html>",
        },
        {
            "role": "public_document_pdf",
            "filename": "fictional-order.pdf",
            "media_type": "application/pdf",
            "content": b"%PDF-1.4 fictional public order",
        },
        {
            "role": "archive_capture",
            "filename": "fictional-capture.wacz",
            "media_type": "application/wacz",
            "content": b"fictional wacz bytes",
        },
        {
            "role": "screenshot",
            "filename": "fictional-page.png",
            "media_type": "image/png",
            "content": b"fictional png bytes",
        },
    ]


def _prepare_payload(**overrides):
    payload = {
        "actor": "admin",
        "passive_discovery_batch_id": "passive-archive-batch-a",
        "candidate_id": "passive-archive-candidate-a",
        "candidate_review_decision": "approved_for_synthetic_capture",
        "candidate_review_reason": "Approve this fictional candidate for the pilot.",
        "requested_url": "https://example.test/notices/1",
        "final_url": "https://example.test/notices/1-final",
        "redirect_chain": [
            {
                "from_url": "https://example.test/notices/1",
                "to_url": "https://example.test/notices/1-final",
                "status_code": 302,
            }
        ],
        "response_status": 200,
        "response_headers": {
            "content-type": "text/html",
            "etag": "fictional-etag",
        },
        "captured_at": "2026-07-21T10:00:00Z",
        "adapter_name": "synthetic-offline-capture",
        "adapter_version": "1.0",
        "capture_files": _capture_files(),
        "reason": "Prepare the synthetic capture provenance pilot.",
        "confirmed": True,
    }
    payload.update(overrides)
    return payload


def _artifact_result(call_number, *, initial_state="registered"):
    return {
        "status": "evidence_artifact_registered",
        "artifact_id": f"evidence-artifact-{call_number}",
        "artifact_event_sha256": str(call_number) * 64,
        "initial_state": initial_state,
        "duplicate_of_artifact_id": None,
    }


def _configure_prepare(
    monkeypatch, *, batch=None, gate=None, request=None, existing=None
):
    monkeypatch.setattr(service, "find_passive_batch", lambda batch_id: batch)
    monkeypatch.setattr(service, "find_gate_decision", lambda gate_id: gate)
    monkeypatch.setattr(service, "find_discovery_request", lambda request_id: request)
    monkeypatch.setattr(service, "find_synthetic_capture", lambda capture_id: existing)
    calls = []

    def register_artifact(**kwargs):
        calls.append(kwargs)
        return _artifact_result(len(calls))

    monkeypatch.setattr(service, "register_artifact", register_artifact)
    monkeypatch.setattr(
        service,
        "_record",
        lambda action, actor, target, event, ip_address: {
            **event,
            "actor": actor,
            "audit_record_id": 1,
            "recorded_at": "2026-07-21T10:00:01+00:00",
        },
    )
    return calls


def test_v38_4_prepares_complete_synthetic_artifact_set(monkeypatch):
    calls = _configure_prepare(
        monkeypatch,
        batch=_batch(),
        gate=_gate(),
        request=_request(),
    )
    result = service.prepare_synthetic_capture(**_prepare_payload())

    assert result["status"] == "synthetic_capture_artifacts_prepared"
    assert result["artifact_registration_count"] == 4
    assert len(calls) == 4
    assert {item["role"] for item in result["capture_manifest"]["files"]} == {
        "primary_html",
        "public_document_pdf",
        "archive_capture",
        "screenshot",
    }
    assert all(
        len(item["content_sha256"]) == 64
        for item in result["capture_manifest"]["files"]
    )
    assert result["capture_manifest"]["redirect_chain"][0]["status_code"] == 302
    assert result["raw_content_recorded"] is False
    assert result["network_request_performed"] is False
    assert result["crawler_execution_performed"] is False
    assert result["browser_capture_performed"] is False
    assert result["source_registered"] is False
    assert result["import_registered"] is False
    assert result["observation_created"] is False


def test_v38_4_blocks_unreviewed_duplicate_candidate_and_sensitive_headers(monkeypatch):
    _configure_prepare(
        monkeypatch,
        batch=_batch(candidates=[_candidate(record_status="duplicate")]),
        gate=_gate(),
        request=_request(),
    )
    result = service.prepare_synthetic_capture(**_prepare_payload())
    assert result["blockers"] == [
        {"key": "accepted_passive_archive_candidate_required"}
    ]

    _configure_prepare(
        monkeypatch,
        batch=_batch(),
        gate=_gate(),
        request=_request(),
    )
    result = service.prepare_synthetic_capture(
        **_prepare_payload(response_headers={"set-cookie": "secret=value"})
    )
    assert result["blockers"] == [
        {"key": "sensitive_response_header_prohibited"}
    ]


def test_v38_4_requires_all_capture_roles(monkeypatch):
    _configure_prepare(
        monkeypatch,
        batch=_batch(),
        gate=_gate(),
        request=_request(),
    )
    result = service.prepare_synthetic_capture(
        **_prepare_payload(capture_files=_capture_files()[:-1])
    )
    assert result["blockers"] == [{"key": "synthetic_capture_roles_incomplete"}]


def _prepared_capture():
    files, _, error = service._normalize_capture_files(_capture_files())
    assert error is None
    registrations = []
    for index, file_record in enumerate(files or [], start=1):
        registrations.append(
            {
                **file_record,
                "artifact_id": f"evidence-artifact-{index}",
                "artifact_event_sha256": str(index) * 64,
                "initial_state": "registered",
                "duplicate_of_artifact_id": None,
            }
        )
    return {
        "synthetic_capture_id": "synthetic-capture-a",
        "synthetic_capture_event_sha256": "d" * 64,
        "capture_manifest_sha256": "e" * 64,
        "provenance_status": "artifacts_prepared",
        "capture_manifest": {
            "case_id": "case-a",
            "purpose": "Preserve fictional public records.",
            "requested_url": "https://example.test/notices/1",
            "final_url": "https://example.test/notices/1-final",
            "captured_at": "2026-07-21T10:00:00+00:00",
            "adapter": {"name": "synthetic-offline-capture", "version": "1.0"},
        },
        "artifact_registrations": registrations,
    }


def _accepted_artifact(registration):
    return {
        "artifact_id": registration["artifact_id"],
        "artifact_state": "accepted",
        "content_sha256": registration["content_sha256"],
        "acquisition_sha256": "f" * 64,
        "state_history": [{"artifact_event_sha256": "9" * 64}],
    }


def _finalize_payload(**overrides):
    payload = {
        "actor": "admin",
        "synthetic_capture_id": "synthetic-capture-a",
        "publisher_or_operator": "Fictional Public Records Office",
        "jurisdiction": "CA-ON",
        "source_type": "archive",
        "terms_and_collection_notes": "Synthetic fixture; no live access occurred.",
        "reason": "Finalize the pre-live-network provenance proof.",
        "confirmed": True,
    }
    payload.update(overrides)
    return payload


def _configure_finalize(monkeypatch, *, prepared=None, artifact_state="accepted"):
    monkeypatch.setattr(service, "find_synthetic_capture", lambda capture_id: prepared)
    registrations = {
        item["artifact_id"]: item for item in prepared["artifact_registrations"]
    }

    def find_artifact(artifact_id):
        artifact = _accepted_artifact(registrations[artifact_id])
        artifact["artifact_state"] = artifact_state
        return artifact

    monkeypatch.setattr(service, "find_artifact", find_artifact)
    monkeypatch.setattr(
        service,
        "register_source",
        lambda **kwargs: {
            "status": "source_record_registered",
            "source_id": "source-record-a",
            "source_event_sha256": "1" * 64,
        },
    )
    monkeypatch.setattr(
        service,
        "register_import_envelope",
        lambda **kwargs: {
            "status": "operational_import_registered",
            "operational_import_id": "operational-import-a",
            "operational_import_event_sha256": "2" * 64,
        },
    )
    monkeypatch.setattr(
        service,
        "_record",
        lambda action, actor, target, event, ip_address: {
            **event,
            "actor": actor,
            "audit_record_id": 2,
            "recorded_at": "2026-07-21T10:10:00+00:00",
        },
    )


def test_v38_4_finalizes_accepted_artifacts_source_and_v37_handoff(monkeypatch):
    prepared = _prepared_capture()
    _configure_finalize(monkeypatch, prepared=prepared)
    result = service.finalize_synthetic_capture_provenance(**_finalize_payload())

    assert result["status"] == "synthetic_capture_provenance_finalized"
    assert result["pre_live_network_gate_satisfied"] is True
    assert all(result["required_proofs"].values())
    assert result["final_binding"]["source_id"] == "source-record-a"
    assert result["final_binding"]["operational_import_id"] == "operational-import-a"
    assert len(result["final_binding"]["artifact_bindings"]) == 4
    assert result["source_registered"] is True
    assert result["import_registered"] is True
    assert result["network_request_performed"] is False
    assert result["automatic_observation_promotion"] is False
    assert result["observation_created"] is False
    assert result["truth_assigned"] is False
    assert result["published"] is False


def test_v38_4_finalize_requires_explicit_v29_acceptance(monkeypatch):
    prepared = _prepared_capture()
    _configure_finalize(monkeypatch, prepared=prepared, artifact_state="registered")
    result = service.finalize_synthetic_capture_provenance(**_finalize_payload())

    assert result["blockers"] == [
        {"key": "accepted_synthetic_capture_artifact_required"}
    ]


def test_v38_4_reuses_completed_provenance(monkeypatch):
    prepared = _prepared_capture()
    prepared["provenance_status"] = "complete"
    prepared["finalization"] = {"pre_live_network_gate_satisfied": True}
    monkeypatch.setattr(service, "find_synthetic_capture", lambda capture_id: prepared)

    result = service.finalize_synthetic_capture_provenance(**_finalize_payload())
    assert result["status"] == "synthetic_capture_provenance_reused"
    assert result["idempotent_replay"] is True
