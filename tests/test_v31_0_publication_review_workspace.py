from src.socmint import publication_review_workspace_v31_0 as workspace


def test_v31_0_builds_read_only_inventory(monkeypatch, tmp_path):
    monkeypatch.setattr(workspace.database, "ensure_configured", lambda: None)
    monkeypatch.setattr(workspace, "_release_records", lambda: [])
    monkeypatch.setattr(workspace, "current_publication_candidates", lambda: [])
    monkeypatch.setattr(
        workspace,
        "current_contribution_decisions",
        lambda: [
            {
                "claim_id": "claim-1",
                "case_id": "case-1",
                "decision": "approved",
                "target_section": "findings",
            }
        ],
    )
    for item in workspace.DOSSIER_CONTRACTS:
        path = tmp_path / item
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("ok", encoding="utf-8")

    result = workspace.build_publication_review_workspace(tmp_path)
    assert result["read_only"] is True
    assert result["publication_ready"] is True
    assert result["approved_contribution_count"] == 1
    assert result["publication_candidate_count"] == 0
    assert result["automatic_publication_performed"] is False
    assert result["dossier_mutated"] is False


def test_v31_0_surfaces_blockers(monkeypatch, tmp_path):
    monkeypatch.setattr(workspace.database, "ensure_configured", lambda: None)
    monkeypatch.setattr(workspace, "_release_records", lambda: [])
    monkeypatch.setattr(workspace, "current_publication_candidates", lambda: [])
    monkeypatch.setattr(
        workspace,
        "current_contribution_decisions",
        lambda: [{"claim_id": "claim-2", "decision": "approved", "target_section": None}],
    )

    result = workspace.build_publication_review_workspace(tmp_path)
    keys = {item["key"] for item in result["blockers"]}
    assert result["publication_ready"] is False
    assert "dossier_contracts_missing" in keys
    assert "approved_contributions_missing_case_binding" in keys
    assert "approved_contributions_missing_target_section" in keys
