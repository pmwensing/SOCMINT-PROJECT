from src.socmint import case_import_pilot_v37_3 as service


IMPORT = {
    "operational_import_id": "import-46",
    "envelope": {"case_id": service.PILOT_CASE_ID},
}


def _staged(text: str, *, state: str = "accepted"):
    return {
        "staged_record_id": "record-1",
        "operational_import_id": "import-46",
        "record_sha256": "a" * 64,
        "initial_state": state,
        "raw_value": text,
        "normalized_value": text.lower(),
        "context": {"synthetic_fixture": True},
    }


def _configure(
    monkeypatch,
    *,
    staged=None,
    assessment=None,
    decision=None,
):
    monkeypatch.setattr(
        service,
        "find_staged_record_projection",
        lambda staged_record_id: staged,
    )
    monkeypatch.setattr(service, "find_import", lambda import_id: IMPORT)
    monkeypatch.setattr(
        service,
        "find_scope_assessment",
        lambda staged_record_id: assessment,
    )
    monkeypatch.setattr(
        service,
        "find_review_decision",
        lambda staged_record_id: decision,
    )
    monkeypatch.setattr(
        service,
        "_record",
        lambda action, actor, target, event, ip_address: {
            **event,
            "actor": actor,
            "audit_record_id": 1,
            "recorded_at": "2026-07-20T01:10:00+00:00",
        },
    )


def _assess(monkeypatch, text: str, *, state: str = "accepted"):
    _configure(monkeypatch, staged=_staged(text, state=state))
    return service.assess_pilot_record(
        actor="admin",
        staged_record_id="record-1",
        reason="Assess fictional pilot record.",
        confirmed=True,
    )


def test_v37_3_classifies_direct_relocation_excluded_and_candidate_records(monkeypatch):
    direct = _assess(monkeypatch, "Inspection record for 46 Montreal Street")
    assert direct["scope_status"] == "in_scope"
    assert direct["candidate_review_required"] is False

    relocation = _assess(
        monkeypatch,
        "559 Macdonnel suitable relocation and mitigation context",
    )
    assert relocation["scope_status"] == "relocation_context"
    assert relocation["relocation_context_only"] is True

    excluded = _assess(monkeypatch, "71 Cowdy unrelated maintenance issue")
    assert excluded["scope_status"] == "out_of_scope"
    assert excluded["out_of_scope"] is True

    candidate = _assess(monkeypatch, "Example Contractor Entity")
    assert candidate["scope_status"] == "candidate_review_required"
    assert candidate["candidate_review_required"] is True


def test_v37_3_scope_assessment_is_idempotent(monkeypatch):
    first = _assess(monkeypatch, "Inspection record for 46 Montreal Street")
    existing = {
        **first,
        "assessment_sha256": first["assessment_sha256"],
    }
    _configure(
        monkeypatch,
        staged=_staged("Inspection record for 46 Montreal Street"),
        assessment=existing,
    )
    replay = service.assess_pilot_record(
        actor="admin",
        staged_record_id="record-1",
        reason="Replay.",
        confirmed=True,
    )
    assert replay["status"] == "case_import_scope_assessment_reused"
    assert replay["idempotent_replay"] is True


def _review(monkeypatch, *, scope_status, state="accepted", decision="accepted", **kwargs):
    assessment = {
        "scope_assessment_id": "assessment-1",
        "scope_event_sha256": "b" * 64,
        "scope_status": scope_status,
    }
    _configure(
        monkeypatch,
        staged=_staged("Synthetic", state=state),
        assessment=assessment,
    )
    return service.record_pilot_review_decision(
        actor="admin",
        staged_record_id="record-1",
        decision=decision,
        quarantine_resolution=kwargs.get("quarantine_resolution"),
        candidate_resolution_reference=kwargs.get("candidate_resolution_reference"),
        reason="Record explicit review decision.",
        confirmed=True,
    )


def test_v37_3_review_rules_block_unsafe_acceptance(monkeypatch):
    duplicate = _review(
        monkeypatch,
        scope_status="in_scope",
        state="duplicate",
    )
    assert duplicate["blockers"] == [{"key": "duplicate_record_must_be_rejected"}]

    excluded = _review(monkeypatch, scope_status="out_of_scope")
    assert excluded["blockers"] == [{"key": "out_of_scope_record_must_be_rejected"}]

    candidate = _review(monkeypatch, scope_status="candidate_review_required")
    assert candidate["blockers"] == [{"key": "candidate_resolution_reference_required"}]

    quarantined = _review(
        monkeypatch,
        scope_status="in_scope",
        state="quarantined",
    )
    assert quarantined["blockers"] == [{"key": "quarantine_resolution_required"}]


def test_v37_3_review_decisions_preserve_relocation_boundary(monkeypatch):
    direct = _review(monkeypatch, scope_status="in_scope")
    assert direct["status"] == "case_import_review_decision_recorded"
    assert direct["observation_promotion_allowed"] is True
    assert direct["issue_claim_support_allowed"] is True

    relocation = _review(monkeypatch, scope_status="relocation_context")
    assert relocation["observation_promotion_allowed"] is True
    assert relocation["relocation_context_only"] is True
    assert relocation["issue_claim_support_allowed"] is False

    candidate = _review(
        monkeypatch,
        scope_status="candidate_review_required",
        candidate_resolution_reference="candidate-decision-1",
    )
    assert candidate["observation_promotion_allowed"] is True
    assert candidate["candidate_resolution_reference"] == "candidate-decision-1"


def test_v37_3_evidence_location_projection_never_uploads_original():
    result = service.build_evidence_location_projection(
        evidence_id="46M-SYNTHETIC-001",
        location_type="local_primary",
        location_id="LOCAL-SYNTHETIC-001",
        path_or_file_id="fixture/vault/item.json",
        sha256="c" * 64,
        verified=True,
        notes="Fictional location projection.",
    )
    assert result["status"] == "evidence_location_projection_ready"
    assert result["original_uploaded_to_github"] is False
    assert result["projection"]["manifest_projection_only"] is True
    assert result["projection"]["original_uploaded_to_github"] is False


def test_v37_3_requires_controlled_case_and_confirmation(monkeypatch):
    _configure(monkeypatch, staged=_staged("46 Montreal Street"))
    monkeypatch.setattr(
        service,
        "find_import",
        lambda import_id: {"envelope": {"case_id": "other-case"}},
    )
    result = service.assess_pilot_record(
        actor="admin",
        staged_record_id="record-1",
        reason="Test.",
        confirmed=True,
    )
    assert result["blockers"] == [{"key": "controlled_pilot_case_required"}]

    _configure(monkeypatch, staged=_staged("46 Montreal Street"))
    result = service.assess_pilot_record(
        actor="admin",
        staged_record_id="record-1",
        reason="Test.",
        confirmed=False,
    )
    assert result["blockers"] == [
        {"key": "explicit_scope_assessment_confirmation_required"}
    ]
