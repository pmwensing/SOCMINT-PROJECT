from src.socmint import import_observation_promotion_v37_4 as service


STAGED = {
    "staged_record_id": "record-1",
    "operational_import_id": "import-1",
    "record_sha256": "a" * 64,
    "initial_state": "accepted",
    "record_type": "entity_reference",
    "normalized_value": "entity alpha",
    "extraction_confidence": 0.9,
}
REVIEW = {
    "review_decision_id": "review-1",
    "review_decision_sha256": "b" * 64,
    "decision": "accepted",
    "observation_promotion_allowed": True,
    "relocation_context_only": False,
    "issue_claim_support_allowed": True,
}
ASSESSMENT = {
    "scope_assessment_id": "assessment-1",
    "scope_event_sha256": "c" * 64,
    "scope_status": "in_scope",
}
IMPORT = {
    "operational_import_event_sha256": "d" * 64,
    "envelope": {
        "case_id": "case_46_montreal",
        "artifact_binding": {"artifact_id": "artifact-1"},
    },
}
UPSTREAM = {
    "status": "evidence_observation_derived",
    "observation_id": "observation-1",
    "observation_sha256": "e" * 64,
    "artifact_event_sha256": "f" * 64,
}


def _configure(
    monkeypatch,
    *,
    staged=STAGED,
    review=REVIEW,
    assessment=ASSESSMENT,
    parent=IMPORT,
    existing=None,
    upstream=UPSTREAM,
):
    monkeypatch.setattr(service, "find_staged_record_projection", lambda record_id: staged)
    monkeypatch.setattr(service, "find_review_decision", lambda record_id: review)
    monkeypatch.setattr(service, "find_scope_assessment", lambda record_id: assessment)
    monkeypatch.setattr(service, "find_import", lambda import_id: parent)
    monkeypatch.setattr(service, "find_promotion", lambda record_id: existing)
    monkeypatch.setattr(service, "derive_observation", lambda **kwargs: upstream)
    monkeypatch.setattr(
        service,
        "_record",
        lambda actor, promotion_id, event, ip_address: {
            **event,
            "actor": actor,
            "audit_record_id": 1,
            "recorded_at": "2026-07-20T01:20:00+00:00",
        },
    )


def _promote(monkeypatch, **config):
    _configure(monkeypatch, **config)
    return service.promote_reviewed_record(
        actor="admin",
        staged_record_id="record-1",
        derivation_method="reviewed_operator_import",
        reason="Promote one explicitly accepted fictional record.",
        confirmed=True,
    )


def test_v37_4_promotes_one_reviewed_record_through_v29(monkeypatch):
    captured = {}
    _configure(monkeypatch)

    def derive(**kwargs):
        captured.update(kwargs)
        return UPSTREAM

    monkeypatch.setattr(service, "derive_observation", derive)
    result = service.promote_reviewed_record(
        actor="admin",
        staged_record_id="record-1",
        derivation_method="reviewed_operator_import",
        reason="Promote one explicitly accepted fictional record.",
        confirmed=True,
    )
    assert result["status"] == "reviewed_import_record_promoted"
    assert captured["artifact_id"] == "artifact-1"
    assert captured["observation_type"] == "entity_reference"
    assert captured["normalized_value"] == "entity alpha"
    assert captured["confirmed"] is True
    assert result["binding"]["observation_id"] == "observation-1"
    assert result["bulk_promotion_performed"] is False
    assert result["automatic_promotion_performed"] is False
    assert result["truth_assigned"] is False
    assert result["export_created"] is False


def test_v37_4_reuses_existing_promotion(monkeypatch):
    existing = {
        "promotion_id": "promotion-existing",
        "staged_record_id": "record-1",
    }
    result = _promote(monkeypatch, existing=existing)
    assert result["status"] == "reviewed_import_record_promotion_reused"
    assert result["idempotent_replay"] is True


def test_v37_4_requires_accepted_review_and_safe_scope(monkeypatch):
    rejected = {**REVIEW, "decision": "rejected", "observation_promotion_allowed": False}
    result = _promote(monkeypatch, review=rejected)
    assert result["blockers"] == [{"key": "accepted_import_review_decision_required"}]

    duplicate = {**STAGED, "initial_state": "duplicate"}
    result = _promote(monkeypatch, staged=duplicate)
    assert result["blockers"] == [{"key": "duplicate_record_cannot_be_promoted"}]

    out_scope = {**ASSESSMENT, "scope_status": "out_of_scope"}
    result = _promote(monkeypatch, assessment=out_scope)
    assert result["blockers"] == [{"key": "out_of_scope_record_cannot_be_promoted"}]


def test_v37_4_preserves_relocation_context_boundary(monkeypatch):
    relocation_review = {
        **REVIEW,
        "relocation_context_only": True,
        "issue_claim_support_allowed": False,
    }
    result = _promote(monkeypatch, review=relocation_review)
    assert result["status"] == "reviewed_import_record_promoted"
    assert result["relocation_context_only"] is True
    assert result["issue_claim_support_allowed"] is False


def test_v37_4_blocks_upstream_failure_and_missing_bindings(monkeypatch):
    result = _promote(
        monkeypatch,
        upstream={"status": "blocked", "blockers": [{"key": "artifact"}]},
    )
    assert result["blockers"] == [
        {"key": "authoritative_observation_derivation_failed"}
    ]
    assert result["upstream_result"]["status"] == "blocked"

    parent = {"envelope": {"case_id": "case_46_montreal"}}
    result = _promote(monkeypatch, parent=parent)
    assert result["blockers"] == [{"key": "import_artifact_binding_required"}]


def test_v37_4_requires_explicit_confirmation(monkeypatch):
    _configure(monkeypatch)
    result = service.promote_reviewed_record(
        actor="admin",
        staged_record_id="record-1",
        derivation_method="reviewed_operator_import",
        reason="Test.",
        confirmed=False,
    )
    assert result["blockers"] == [
        {"key": "explicit_single_record_promotion_confirmation_required"}
    ]
