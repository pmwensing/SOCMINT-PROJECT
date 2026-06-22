from src.socmint import immutable_published_revision_v31_5 as published


REVISION = {
    "draft_revision_id": "draft-dossier-revision-1",
    "draft_revision_sha256": "draft-sha",
    "publication_candidate_id": "publication-candidate-1",
    "publication_candidate_sha256": "candidate-sha",
    "dossier_contribution_id": "contribution-1",
    "source_manifest_sha256": "source-sha",
    "draft_sections_sha256": "sections-sha",
    "draft_sections": [{"section_id": "key_findings"}],
    "candidate_contribution_entry": {"claim_id": "claim-1"},
    "case_id": "case-1",
    "subject_id": 7,
}

APPROVAL = {
    "release_approval_id": "human-release-approval-1",
    "release_approval_sha256": "approval-sha",
    "result_status": "approved",
    "draft_revision_id": "draft-dossier-revision-1",
    "draft_revision_sha256": "draft-sha",
    "editorial_validation_id": "editorial-validation-1",
    "editorial_validation_sha256": "validation-sha",
    "release_scope": "internal",
    "publication_eligibility": {"eligible": True},
}


def test_v31_5_requires_approved_human_release(monkeypatch):
    monkeypatch.setattr(published, "find_draft_revision", lambda revision_id: REVISION)
    monkeypatch.setattr(published, "latest_release_decision", lambda revision_id: None)

    result = published.create_immutable_published_revision(
        publisher="admin",
        draft_revision_id="draft-dossier-revision-1",
        publication_label="Release 1",
        publication_note="Approved release",
        reason="operator request",
        confirmed=True,
    )

    assert result["status"] == "blocked"
    assert result["blockers"][0]["key"] == "approved_human_release_decision_required"


def test_v31_5_creates_sealed_revision_without_mutating_sources(monkeypatch):
    monkeypatch.setattr(published, "find_draft_revision", lambda revision_id: REVISION)
    monkeypatch.setattr(published, "latest_release_decision", lambda revision_id: APPROVAL)
    monkeypatch.setattr(published, "published_revision_history", lambda: [])
    monkeypatch.setattr(
        published,
        "_record",
        lambda publisher, target_value, event, ip_address: {**event, "publisher": publisher},
    )

    result = published.create_immutable_published_revision(
        publisher="admin",
        draft_revision_id="draft-dossier-revision-1",
        publication_label="Release 1",
        publication_note="Approved release",
        reason="operator request",
        confirmed=True,
    )

    assert result["status"] == "published_revision_created"
    assert result["revision_state"] == "published"
    assert result["immutable"] is True
    assert result["published_revision_id"].startswith("published-dossier-revision-")
    assert result["release_approval_id"] == "human-release-approval-1"
    assert result["draft_revision_mutated"] is False
    assert result["release_approval_mutated"] is False
    assert result["prior_published_revision_mutated"] is False
    assert result["external_transmission_performed"] is False


def test_v31_5_prevents_reusing_release_approval(monkeypatch):
    monkeypatch.setattr(published, "find_draft_revision", lambda revision_id: REVISION)
    monkeypatch.setattr(published, "latest_release_decision", lambda revision_id: APPROVAL)
    monkeypatch.setattr(
        published,
        "published_revision_history",
        lambda: [{"release_approval_sha256": "approval-sha"}],
    )

    result = published.create_immutable_published_revision(
        publisher="admin",
        draft_revision_id="draft-dossier-revision-1",
        publication_label="Release 1",
        publication_note="Approved release",
        reason="operator request",
        confirmed=True,
    )

    assert result["status"] == "blocked"
    assert result["blockers"][0]["key"] == "release_approval_already_published"
