from src.socmint import draft_dossier_revision_v31_2 as revision


CANDIDATE = {
    "publication_candidate_id": "publication-candidate-1",
    "publication_candidate_sha256": "candidate-sha",
    "candidate_state": "proposed",
    "dossier_contribution_id": "dossier-contribution-1",
    "candidate_binding_sha256": "binding-sha",
    "claim_id": "claim-1",
    "case_id": "case-1",
    "entity_id": "entity-1",
    "target_section": "key_findings",
}


def test_v31_2_requires_proposed_candidate(monkeypatch):
    monkeypatch.setattr(revision, "find_candidate", lambda candidate_id: None)

    result = revision.assemble_draft_dossier_revision(
        actor="admin",
        publication_candidate_id="missing",
        revision_label="Draft 1",
        editorial_note="Initial assembly",
        reason="operator request",
        confirmed=True,
    )

    assert result["status"] == "blocked"
    assert result["blockers"][0]["key"] == "proposed_publication_candidate_required"
    assert result["publication_performed"] is False


def test_v31_2_assembles_deterministic_draft_without_publication(monkeypatch):
    monkeypatch.setattr(revision, "find_candidate", lambda candidate_id: CANDIDATE)
    monkeypatch.setattr(revision, "draft_revision_history", lambda: [])
    monkeypatch.setattr(
        revision,
        "build_dossier_assembly_workspace",
        lambda case_id, subject_id=None: {
            "schema": "socmint.dossier_assembly_workspace.v21_0",
            "version": "v21.0.0",
            "status": "ready_for_arrangement",
            "source_package": {
                "package_id": "package-1",
                "manifest_sha256": "manifest-sha",
            },
            "sections": [{"section_id": "key_findings", "findings": []}],
            "gaps": [],
            "gap_count": 0,
        },
    )
    monkeypatch.setattr(
        revision,
        "_record",
        lambda actor, target_value, event, ip_address: {**event, "actor": actor},
    )

    result = revision.assemble_draft_dossier_revision(
        actor="admin",
        publication_candidate_id="publication-candidate-1",
        revision_label="Draft 1",
        editorial_note="Initial assembly",
        reason="operator request",
        confirmed=True,
        subject_id=7,
    )

    assert result["status"] == "draft_dossier_revision_assembled"
    assert result["revision_state"] == "draft"
    assert result["draft_revision_id"].startswith("draft-dossier-revision-")
    assert result["publication_candidate_id"] == "publication-candidate-1"
    assert result["source_manifest"]["source_package_id"] == "package-1"
    assert result["candidate_contribution_entry"]["claim_id"] == "claim-1"
    assert result["source_dossier_mutated"] is False
    assert result["release_approval_performed"] is False
    assert result["publication_performed"] is False
    assert result["published_revision_mutated"] is False
