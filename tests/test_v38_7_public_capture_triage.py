from __future__ import annotations

from src.socmint import public_capture_triage_v38_7 as service


def _source(
    source_id: str,
    *,
    canonical_url: str,
    captured_at: str,
    content_sha256: str,
) -> dict:
    return {
        "source_id": source_id,
        "source_event_sha256": (source_id[-1] * 64),
        "case_id": "case-a",
        "source_type": "official_record",
        "publisher_or_operator": "Fictional public authority",
        "original_or_derived": "original",
        "capture_sha256": (source_id[-1] * 64),
        "capture": {
            "canonical_url": canonical_url,
            "retrieved_url": canonical_url,
            "captured_at": captured_at,
            "content_sha256": content_sha256,
            "capture_artifact_id": f"artifact-{source_id}",
            "artifact_binding": {
                "artifact_event_sha256": (source_id[-1] * 64),
            },
            "adapter_name": "public-http",
            "adapter_version": "v38.5.0",
        },
    }


def _sources() -> dict[str, dict]:
    canonical = "https://records.example.test/public-notice"
    return {
        "source-a": _source(
            "source-a",
            canonical_url=canonical,
            captured_at="2026-07-20T10:00:00Z",
            content_sha256="1" * 64,
        ),
        "source-b": _source(
            "source-b",
            canonical_url=canonical,
            captured_at="2026-07-20T11:00:00Z",
            content_sha256="1" * 64,
        ),
        "source-c": _source(
            "source-c",
            canonical_url=canonical,
            captured_at="2026-07-20T12:00:00Z",
            content_sha256="2" * 64,
        ),
        "source-d": _source(
            "source-d",
            canonical_url="https://outside.example.test/unrelated",
            captured_at="2026-07-20T13:00:00Z",
            content_sha256="3" * 64,
        ),
    }


def _relevance() -> list[dict]:
    return [
        {
            "source_id": "source-a",
            "classification": "direct_case",
            "rationale": "Contains the fictional case order identifier.",
            "matched_terms": ["ORDER-TEST-001"],
            "matched_entities": ["Fictional Authority"],
            "limitations": [],
        },
        {
            "source_id": "source-b",
            "classification": "direct_case",
            "rationale": "Duplicate capture of the same fictional order.",
            "matched_terms": ["ORDER-TEST-001"],
            "matched_entities": [],
            "limitations": ["Exact duplicate capture."],
        },
        {
            "source_id": "source-c",
            "classification": "candidate_review",
            "rationale": "The content hash changed and requires analyst review.",
            "matched_terms": [],
            "matched_entities": [],
            "limitations": ["No factual significance assigned to the change."],
        },
        {
            "source_id": "source-d",
            "classification": "out_of_scope",
            "rationale": "The source concerns an unrelated fictional address.",
            "matched_terms": [],
            "matched_entities": [],
            "limitations": [],
        },
    ]


def _configure(monkeypatch, *, existing=None):
    sources = _sources()
    monkeypatch.setattr(service, "find_source", lambda source_id: sources.get(source_id))
    monkeypatch.setattr(service, "groups_for_sources", lambda source_ids: [])
    monkeypatch.setattr(service, "find_triage", lambda triage_id: existing)
    monkeypatch.setattr(
        service,
        "_record",
        lambda actor, triage_id, event, ip_address: {
            **event,
            "actor": actor,
            "audit_record_id": 1,
            "recorded_at": "2026-07-20T14:00:00+00:00",
        },
    )


def _triage(monkeypatch):
    _configure(monkeypatch)
    return service.triage_public_captures(
        actor="analyst",
        case_id="case-a",
        source_ids=["source-d", "source-c", "source-b", "source-a"],
        relevance_assessments=_relevance(),
        reason="Triage fictional registered public captures.",
        confirmed=True,
    )


def test_v38_7_computes_duplicates_recaptures_and_hash_changes(monkeypatch):
    result = _triage(monkeypatch)
    assert result["status"] == "public_capture_triage_recorded"
    assert result["counts"] == {
        "sources": 4,
        "support_eligible": 1,
        "duplicate_groups": 1,
        "mirror_proposals": 1,
        "recapture_groups": 1,
        "change_summaries": 2,
        "candidate_review": 1,
        "out_of_scope": 1,
    }
    duplicate = result["duplicate_groups"][0]
    assert duplicate["primary_source_id"] == "source-a"
    assert duplicate["support_suppressed_source_ids"] == ["source-b"]
    assert duplicate["deterministic_primary_suggestion_only"] is True

    changes = result["change_summaries"]
    assert [item["change_state"] for item in changes] == [
        "unchanged",
        "content_hash_changed",
    ]
    assert all(item["factual_significance_assigned"] is False for item in changes)
    assert all(item["causation_assigned"] is False for item in changes)


def test_v38_7_separates_relevance_from_duplicate_support(monkeypatch):
    result = _triage(monkeypatch)
    entries = {item["source_id"]: item for item in result["source_triage"]}
    assert entries["source-a"]["support_eligible"] is True
    assert entries["source-a"]["v37_handoff_eligible"] is True
    assert entries["source-b"]["duplicate_secondary"] is True
    assert entries["source-b"]["support_eligible"] is False
    assert entries["source-c"]["review_required"] is True
    assert entries["source-c"]["v37_handoff_eligible"] is False
    assert entries["source-d"]["out_of_scope"] is True
    assert entries["source-d"]["support_eligible"] is False
    assert result["observation_created"] is False
    assert result["truth_assigned"] is False


def test_v38_7_requires_evidence_for_direct_case_relevance(monkeypatch):
    _configure(monkeypatch)
    relevance = _relevance()
    relevance[0] = {
        **relevance[0],
        "matched_terms": [],
        "matched_entities": [],
    }
    result = service.triage_public_captures(
        actor="analyst",
        case_id="case-a",
        source_ids=list(_sources()),
        relevance_assessments=relevance,
        reason="Attempt incomplete triage.",
        confirmed=True,
    )
    assert result["blockers"] == [
        {"key": "direct_case_relevance_evidence_required"}
    ]


def test_v38_7_mirror_proposal_requires_explicit_v36_confirmation(monkeypatch):
    triage = _triage(monkeypatch)
    proposal = triage["mirror_proposals"][0]
    monkeypatch.setattr(service, "find_triage", lambda triage_id: triage)
    calls = []

    def assess(**kwargs):
        calls.append(kwargs)
        return {
            "status": "source_independence_assessed",
            "independence_group_id": "source-independence-group-test",
            "relationship": "mirror",
        }

    monkeypatch.setattr(service, "assess_source_independence", assess)
    blocked = service.confirm_mirror_proposal(
        actor="analyst",
        capture_triage_id=triage["capture_triage_id"],
        mirror_proposal_id=proposal["mirror_proposal_id"],
        reason="Confirm exact-hash mirror relationship.",
        confirmed=False,
    )
    assert blocked["blockers"] == [
        {"key": "explicit_mirror_assessment_confirmation_required"}
    ]
    assert calls == []

    result = service.confirm_mirror_proposal(
        actor="analyst",
        capture_triage_id=triage["capture_triage_id"],
        mirror_proposal_id=proposal["mirror_proposal_id"],
        reason="Confirm exact-hash mirror relationship.",
        confirmed=True,
    )
    assert result["status"] == "capture_mirror_proposal_confirmed"
    assert result["independence_assessed"] is True
    assert len(calls) == 1
    assert calls[0]["relationship"] == "mirror"
    assert calls[0]["source_ids"] == ["source-a", "source-b"]


def test_v38_7_handoff_is_explicit_primary_only_and_does_not_stage(monkeypatch):
    triage = _triage(monkeypatch)
    monkeypatch.setattr(service, "find_triage", lambda triage_id: triage)
    calls = []

    def register(**kwargs):
        calls.append(kwargs)
        return {
            "status": "operational_import_registered",
            "operational_import_id": "operational-import-test",
        }

    monkeypatch.setattr(service, "register_import_envelope", register)
    result = service.handoff_capture_to_v37(
        actor="analyst",
        capture_triage_id=triage["capture_triage_id"],
        source_id="source-a",
        original_filename="public-notice.html",
        media_type="text/html",
        export_format="html",
        imported_at="2026-07-20T14:10:00Z",
        reason="Hand off the selected primary capture for separate review.",
        confirmed=True,
    )
    assert result["status"] == "public_capture_handed_off_to_v37"
    assert result["import_registered"] is True
    assert result["import_records_staged"] is False
    assert result["observation_created"] is False
    assert len(calls) == 1
    assert calls[0]["artifact_id"] == "artifact-source-a"
    assert calls[0]["collection_context"]["operator_selected"] is True

    blocked = service.handoff_capture_to_v37(
        actor="analyst",
        capture_triage_id=triage["capture_triage_id"],
        source_id="source-b",
        original_filename="duplicate.html",
        media_type="text/html",
        export_format="html",
        imported_at="2026-07-20T14:10:00Z",
        reason="Attempt duplicate handoff.",
        confirmed=True,
    )
    assert blocked["blockers"] == [
        {"key": "triaged_source_not_eligible_for_v37_handoff"}
    ]
    assert len(calls) == 1
