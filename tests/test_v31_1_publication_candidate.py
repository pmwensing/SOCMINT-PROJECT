from src.socmint import publication_candidate_v31_1 as candidate


APPROVED = {
    "dossier_contribution_id": "dossier-contribution-approved",
    "dossier_contribution_sha256": "abc123",
    "dossier_contribution_authorized": True,
    "decision": "approved",
    "claim_id": "claim-1",
    "case_id": "case-1",
    "entity_id": "entity-1",
    "target_section": "findings",
}


def test_v31_1_requires_approved_v30_contribution(monkeypatch):
    monkeypatch.setattr(candidate, "current_contribution_decisions", lambda: [])

    result = candidate.create_publication_candidate(
        actor="admin",
        dossier_contribution_id="missing",
        publication_purpose="release",
        release_scope="internal",
        rationale="ready",
        reason="test",
        confirmed=True,
    )

    assert result["status"] == "blocked"
    assert result["blockers"][0]["key"] == "approved_v30_dossier_contribution_required"
    assert result["publication_performed"] is False


def test_v31_1_creates_deterministic_append_only_candidate(monkeypatch):
    monkeypatch.setattr(candidate, "current_contribution_decisions", lambda: [APPROVED])
    monkeypatch.setattr(candidate, "candidate_history", lambda: [])
    monkeypatch.setattr(
        candidate,
        "_record",
        lambda actor, target_value, event, ip_address: {**event, "actor": actor},
    )

    result = candidate.create_publication_candidate(
        actor="admin",
        dossier_contribution_id="dossier-contribution-approved",
        publication_purpose="controlled release",
        release_scope="internal analyst audience",
        rationale="approved contribution is ready for draft assembly",
        reason="operator request",
        confirmed=True,
    )

    assert result["status"] == "publication_candidate_recorded"
    assert result["candidate_state"] == "proposed"
    assert result["publication_candidate_id"].startswith("publication-candidate-")
    assert result["dossier_contribution_id"] == "dossier-contribution-approved"
    assert result["draft_revision_created"] is False
    assert result["release_approval_performed"] is False
    assert result["publication_performed"] is False
    assert result["dossier_mutated"] is False


def test_v31_1_withdrawal_preserves_candidate_history(monkeypatch):
    current = {
        "publication_candidate_id": "publication-candidate-1",
        "publication_candidate_sha256": "old-sha",
        "candidate_state": "proposed",
        "event_type": candidate.ACTION,
        "dossier_contribution_id": "dossier-contribution-approved",
        "claim_id": "claim-1",
        "case_id": "case-1",
        "entity_id": "entity-1",
        "target_section": "findings",
        "publication_purpose": "release",
        "release_scope": "internal",
        "rationale": "ready",
        "candidate_binding": {"dossier_contribution_id": "dossier-contribution-approved"},
        "candidate_binding_sha256": "binding-sha",
    }
    monkeypatch.setattr(candidate, "find_candidate", lambda candidate_id: current)
    monkeypatch.setattr(
        candidate,
        "_record",
        lambda actor, target_value, event, ip_address: {**event, "actor": actor},
    )

    result = candidate.update_publication_candidate_state(
        actor="admin",
        candidate_id="publication-candidate-1",
        candidate_state="withdrawn",
        reason="superseded before draft assembly",
        confirmed=True,
    )

    assert result["status"] == "publication_candidate_state_recorded"
    assert result["candidate_state"] == "withdrawn"
    assert result["supersedes_candidate_event_sha256"] == "old-sha"
    assert result["publication_performed"] is False
