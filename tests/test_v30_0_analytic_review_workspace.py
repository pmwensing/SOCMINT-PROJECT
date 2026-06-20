from src.socmint import analytic_review_workspace_v30_0 as workspace


def _base(monkeypatch):
    monkeypatch.setattr(workspace.database, "ensure_configured", lambda: None)
    monkeypatch.setattr(workspace, "current_artifacts", lambda: [])
    monkeypatch.setattr(workspace, "observations", lambda: [])
    monkeypatch.setattr(workspace, "quality_assessments", lambda: [])
    monkeypatch.setattr(workspace, "contribution_reviews", lambda: [])
    monkeypatch.setattr(workspace, "current_claims", lambda: [])
    monkeypatch.setattr(workspace, "claim_linkages", lambda: [])
    monkeypatch.setattr(workspace, "current_conflicts", lambda: [])
    monkeypatch.setattr(workspace, "confidence_assessments", lambda: [])
    monkeypatch.setattr(workspace, "current_review_decisions", lambda: [])
    monkeypatch.setattr(workspace, "_claim_inventory", lambda: [])
    monkeypatch.setattr(workspace, "_review_decisions", lambda: [])
    monkeypatch.setattr(workspace, "list_enrichment_review_items", lambda limit=500: [])
    monkeypatch.setattr(workspace, "review_summary", lambda: {})


def test_v30_0_builds_read_only_inventory(monkeypatch):
    _base(monkeypatch)
    monkeypatch.setattr(workspace, "current_artifacts", lambda: [{"artifact_id": "artifact-1"}])
    monkeypatch.setattr(workspace, "observations", lambda: [{"artifact_id": "artifact-1", "observation_id": "obs-1", "observation_type": "username", "normalized_value": "alice"}])
    monkeypatch.setattr(workspace, "quality_assessments", lambda: [{"quality_assessment_id": "qa-1", "quality_score": 90, "trust_tier": "trusted"}])
    monkeypatch.setattr(workspace, "contribution_reviews", lambda: [{"quality_assessment_id": "qa-1", "decision": "approved"}])
    monkeypatch.setattr(workspace, "_claim_inventory", lambda: [{"id": 1, "subject_id": 7, "assertion_type": "username", "normalized_value": "alice", "confidence": 0.9, "validation_state": "approved"}])
    result = workspace.build_analytic_review_workspace()
    assert result["status"] == "ready"
    assert result["read_only"] is True
    assert result["evidence_count"] == 1
    assert result["claim_count"] == 1
    assert result["claim_source_linkage_count"] == 0
    assert result["analytic_conflict_count"] == 0
    assert result["analytic_confidence_count"] == 0
    assert result["human_analytic_review_count"] == 0
    assert result["dossier_contribution_summary"]["approved"] == 1
    assert result["dossier_mutated"] is False


def test_v30_0_surfaces_contradictions(monkeypatch):
    _base(monkeypatch)
    monkeypatch.setattr(workspace, "quality_assessments", lambda: [{"quality_assessment_id": "qa-pending", "quality_score": 70, "trust_tier": "supported"}])
    monkeypatch.setattr(workspace, "_claim_inventory", lambda: [
        {"id": 1, "subject_id": 4, "assertion_type": "location", "normalized_value": "A", "confidence": None, "validation_state": "needs_review"},
        {"id": 2, "subject_id": 4, "assertion_type": "location", "normalized_value": "B", "confidence": 0.5, "validation_state": "pending"},
    ])
    result = workspace.build_analytic_review_workspace()
    assert result["contradiction_count"] == 1
    assert result["dossier_contribution_summary"]["pending_review"] == 1
    keys = {item["key"] for item in result["analytic_findings"]}
    assert "contradictory_claim_values_present" in keys
    assert "claims_require_review" in keys
