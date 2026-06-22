from src.socmint import editorial_validation_v31_3 as validation


REVISION = {
    "draft_revision_id": "draft-dossier-revision-1",
    "draft_revision_sha256": "draft-sha",
    "revision_state": "draft",
    "publication_candidate_id": "publication-candidate-1",
    "publication_candidate_sha256": "candidate-sha",
    "case_id": "case-1",
    "subject_id": 7,
    "target_section": "key_findings",
    "source_manifest": {"source_package_id": "package-1"},
    "source_manifest_sha256": "source-sha",
    "draft_sections": [{"section_id": "key_findings"}],
    "draft_sections_sha256": "sections-sha",
    "candidate_contribution_entry": {"dossier_contribution_id": "contribution-1"},
    "assembly_gap_count": 0,
    "source_dossier_status": "ready_for_arrangement",
}

CANDIDATE = {
    "publication_candidate_id": "publication-candidate-1",
    "publication_candidate_sha256": "candidate-sha",
    "candidate_state": "proposed",
    "release_scope": "internal",
}

ACKNOWLEDGEMENTS = {
    "provenance_reviewed": True,
    "privacy_reviewed": True,
    "legal_basis_confirmed": True,
    "audience_scope_confirmed": True,
}


def test_v31_3_requires_draft_revision(monkeypatch):
    monkeypatch.setattr(validation, "find_draft_revision", lambda revision_id: None)

    result = validation.run_editorial_validation(
        actor="admin",
        draft_revision_id="missing",
        editorial_summary="Reviewed",
        policy_acknowledgements=ACKNOWLEDGEMENTS,
        reason="operator request",
        confirmed=True,
    )

    assert result["status"] == "blocked"
    assert result["blockers"][0]["key"] == "draft_dossier_revision_required"
    assert result["publication_performed"] is False


def test_v31_3_records_passing_gate_without_release_approval(monkeypatch):
    monkeypatch.setattr(validation, "find_draft_revision", lambda revision_id: REVISION)
    monkeypatch.setattr(validation, "find_candidate", lambda candidate_id: CANDIDATE)
    monkeypatch.setattr(validation, "editorial_validation_history", lambda: [])
    monkeypatch.setattr(
        validation,
        "_record",
        lambda actor, target_value, event, ip_address: {**event, "actor": actor},
    )

    result = validation.run_editorial_validation(
        actor="admin",
        draft_revision_id="draft-dossier-revision-1",
        editorial_summary="Provenance and policy review complete",
        policy_acknowledgements=ACKNOWLEDGEMENTS,
        reason="operator request",
        confirmed=True,
    )

    assert result["status"] == "editorial_validation_recorded"
    assert result["gate_status"] == "passed"
    assert result["blocker_count"] == 0
    assert result["next_action"] == "request_human_release_approval"
    assert result["draft_revision_mutated"] is False
    assert result["release_approval_performed"] is False
    assert result["publication_performed"] is False


def test_v31_3_external_scope_requires_redaction_review(monkeypatch):
    external_candidate = {**CANDIDATE, "release_scope": "external"}
    monkeypatch.setattr(validation, "find_draft_revision", lambda revision_id: REVISION)
    monkeypatch.setattr(validation, "find_candidate", lambda candidate_id: external_candidate)
    monkeypatch.setattr(validation, "editorial_validation_history", lambda: [])
    monkeypatch.setattr(
        validation,
        "_record",
        lambda actor, target_value, event, ip_address: {**event, "actor": actor},
    )

    result = validation.run_editorial_validation(
        actor="admin",
        draft_revision_id="draft-dossier-revision-1",
        editorial_summary="External review incomplete",
        policy_acknowledgements=ACKNOWLEDGEMENTS,
        reason="operator request",
        confirmed=True,
    )

    assert result["status"] == "editorial_validation_recorded"
    assert result["gate_status"] == "needs_revision"
    assert "redaction_reviewed" in {item["key"] for item in result["blockers"]}
    assert result["next_action"] == "revise_draft_dossier_revision"
