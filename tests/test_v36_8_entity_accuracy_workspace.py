from __future__ import annotations

from src.socmint import entity_accuracy_workspace_v36_8 as workspace


def _configure(monkeypatch):
    monkeypatch.setattr(
        workspace,
        "current_sources",
        lambda: [
            {"source_id": "source-1", "reliability_assessed": False},
            {"source_id": "source-2", "reliability_assessed": True},
        ],
    )
    monkeypatch.setattr(
        workspace,
        "current_observations",
        lambda: [
            {
                "canonical_observation_id": "observation-1",
                "observation_state": "quarantined",
            }
        ],
    )
    monkeypatch.setattr(
        workspace,
        "current_candidates",
        lambda: [
            {"candidate_id": "candidate-1", "decision_recorded": False}
        ],
    )
    monkeypatch.setattr(
        workspace,
        "current_independence_assessments",
        lambda: [],
    )
    monkeypatch.setattr(
        workspace,
        "current_verifications",
        lambda: [
            {
                "claim_id": "claim-1",
                "source_ids": ["source-1", "source-2"],
                "confidence_band": "moderate",
                "independence_context": {"score": 0},
                "ranking": {"tie_at_top": True},
                "unresolved_conflict_ids": ["conflict-1"],
            }
        ],
    )
    monkeypatch.setattr(
        workspace,
        "current_relationship_assessments",
        lambda: [
            {
                "relationship_timeline_assessment_id": "relationship-1",
                "relationship_type": "co_occurrence",
            }
        ],
    )
    monkeypatch.setattr(workspace, "current_snapshots", lambda: [])


def test_v36_8_builds_integrated_read_only_workspace(monkeypatch):
    _configure(monkeypatch)
    result = workspace.build_entity_accuracy_workspace()
    assert result["schema"] == "socmint.entity_accuracy_workspace.v36_8"
    assert result["status"] == "ready"
    assert result["read_only"] is True
    assert result["automatic_truth_assignment"] is False
    assert result["automatic_entity_merge"] is False
    assert result["automatic_dossier_publication"] is False
    assert result["summary"] == {
        "source_count": 2,
        "canonical_observation_count": 1,
        "entity_candidate_count": 1,
        "source_independence_group_count": 0,
        "claim_verification_count": 1,
        "relationship_timeline_count": 1,
        "dossier_snapshot_count": 0,
        "finding_count": 7,
    }
    assert result["controls"]["human_review_gate"] == "v30.5"
    assert result["controls"]["dossier_contribution_gate"] == "v30.6"
    assert result["controls"]["write_actions_exposed_by_workspace"] == []


def test_v36_8_surfaces_integrity_and_review_findings(monkeypatch):
    _configure(monkeypatch)
    result = workspace.build_entity_accuracy_workspace()
    findings = {item["key"]: item for item in result["findings"]}
    assert set(findings) == {
        "source_reliability_pending",
        "canonical_observations_quarantined",
        "entity_candidates_waiting_decision",
        "source_independence_unassessed",
        "alternative_ranking_tied",
        "verified_claims_disputed",
        "dossier_snapshot_missing",
    }
    assert findings["source_independence_unassessed"]["severity"] == (
        "integrity_alert"
    )
    assert findings["verified_claims_disputed"]["count"] == 1
    assert findings["dossier_snapshot_missing"]["count"] == 1


def test_v36_8_empty_workspace_is_safe_and_ready(monkeypatch):
    for name in (
        "current_sources",
        "current_observations",
        "current_candidates",
        "current_independence_assessments",
        "current_verifications",
        "current_relationship_assessments",
        "current_snapshots",
    ):
        monkeypatch.setattr(workspace, name, lambda: [])
    result = workspace.build_entity_accuracy_workspace()
    assert result["status"] == "ready"
    assert result["summary"]["finding_count"] == 0
    assert result["findings"] == []
    assert result["controls"]["write_actions_exposed_by_workspace"] == []
