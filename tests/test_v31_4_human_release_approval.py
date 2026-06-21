from src.socmint import human_release_approval_v31_4 as approval


REVISION = {
    "draft_revision_id": "draft-dossier-revision-1",
    "draft_revision_sha256": "draft-sha",
    "publication_candidate_id": "publication-candidate-1",
    "publication_candidate_sha256": "candidate-sha",
    "source_manifest_sha256": "source-sha",
    "draft_sections_sha256": "sections-sha",
    "case_id": "case-1",
    "subject_id": 7,
}

PASSED_VALIDATION = {
    "editorial_validation_id": "editorial-validation-1",
    "editorial_validation_sha256": "validation-sha",
    "draft_revision_id": "draft-dossier-revision-1",
    "draft_revision_sha256": "draft-sha",
    "gate_status": "passed",
    "release_scope": "internal",
}


def test_v31_4_requires_editorial_validation(monkeypatch):
    monkeypatch.setattr(approval, "find_draft_revision", lambda revision_id: REVISION)
    monkeypatch.setattr(approval, "latest_editorial_validation", lambda revision_id: None)

    result = approval.record_human_release_decision(
        reviewer="admin",
        draft_revision_id="draft-dossier-revision-1",
        decision="approve",
        note="Ready",
        reason="operator request",
        confirmed=True,
    )

    assert result["status"] == "blocked"
    assert result["blockers"][0]["key"] == "editorial_validation_required"
    assert result["publication_performed"] is False


def test_v31_4_approve_requires_passing_gate(monkeypatch):
    failed = {**PASSED_VALIDATION, "gate_status": "needs_revision"}
    monkeypatch.setattr(approval, "find_draft_revision", lambda revision_id: REVISION)
    monkeypatch.setattr(approval, "latest_editorial_validation", lambda revision_id: failed)

    result = approval.record_human_release_decision(
        reviewer="admin",
        draft_revision_id="draft-dossier-revision-1",
        decision="approve",
        note="Ready",
        reason="operator request",
        confirmed=True,
    )

    assert result["status"] == "blocked"
    assert result["blockers"][0]["key"] == "passing_editorial_validation_required"


def test_v31_4_records_explicit_human_approval_without_publication(monkeypatch):
    monkeypatch.setattr(approval, "find_draft_revision", lambda revision_id: REVISION)
    monkeypatch.setattr(
        approval,
        "latest_editorial_validation",
        lambda revision_id: PASSED_VALIDATION,
    )
    monkeypatch.setattr(approval, "release_approval_history", lambda: [])
    monkeypatch.setattr(
        approval,
        "_record",
        lambda reviewer, target_value, event, ip_address: {
            **event,
            "reviewer": reviewer,
        },
    )

    result = approval.record_human_release_decision(
        reviewer="admin",
        draft_revision_id="draft-dossier-revision-1",
        decision="approve",
        note="Human review complete",
        reason="operator request",
        confirmed=True,
    )

    assert result["status"] == "approved"
    assert result["publication_eligibility"]["eligible"] is True
    assert result["next_action"] == "create_immutable_published_revision"
    assert result["draft_revision_mutated"] is False
    assert result["editorial_validation_mutated"] is False
    assert result["publication_performed"] is False
    assert result["published_revision_created"] is False


def test_v31_4_return_and_hold_do_not_enable_publication(monkeypatch):
    monkeypatch.setattr(approval, "find_draft_revision", lambda revision_id: REVISION)
    monkeypatch.setattr(
        approval,
        "latest_editorial_validation",
        lambda revision_id: PASSED_VALIDATION,
    )
    monkeypatch.setattr(approval, "release_approval_history", lambda: [])
    monkeypatch.setattr(
        approval,
        "_record",
        lambda reviewer, target_value, event, ip_address: event,
    )

    returned = approval.record_human_release_decision(
        reviewer="admin",
        draft_revision_id="draft-dossier-revision-1",
        decision="return",
        note="Revise wording",
        reason="editorial correction",
        confirmed=True,
    )
    held = approval.record_human_release_decision(
        reviewer="admin",
        draft_revision_id="draft-dossier-revision-1",
        decision="hold",
        note="Awaiting direction",
        reason="supervisory hold",
        confirmed=True,
    )

    assert returned["status"] == "returned"
    assert returned["publication_eligibility"]["eligible"] is False
    assert held["status"] == "held"
    assert held["publication_eligibility"]["eligible"] is False
