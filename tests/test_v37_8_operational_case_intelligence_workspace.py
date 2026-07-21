from src.socmint import operational_case_intelligence_workspace_v37_8 as workspace


def test_v37_8_builds_integrated_read_only_workspace(monkeypatch):
    monkeypatch.setattr(
        workspace,
        "build_guided_analyst_workflow",
        lambda: {
            "summary": {"import_count": 2, "finding_count": 1},
            "findings": [{"key": "review_pending"}],
        },
    )
    monkeypatch.setattr(
        workspace,
        "build_relationship_chronology",
        lambda: {"summary": {"entry_count": 3}, "entries": []},
    )
    monkeypatch.setattr(
        workspace,
        "current_export_readiness_records",
        lambda: [
            {"readiness_status": "ready"},
            {"readiness_status": "not_ready"},
        ],
    )
    result = workspace.build_operational_case_intelligence_workspace()
    assert result["schema"] == "socmint.operational_case_intelligence_workspace.v37_8"
    assert result["read_only"] is True
    assert result["summary"] == {
        "import_count": 2,
        "finding_count": 1,
        "chronology_entry_count": 3,
        "export_readiness_record_count": 2,
        "export_ready_count": 1,
    }
    assert result["findings"] == [{"key": "review_pending"}]
    assert result["controls"]["write_actions_exposed_by_workspace"] == []
    assert result["controls"]["automatic_collection"] is False
    assert result["controls"]["automatic_observation_promotion"] is False
    assert result["controls"]["automatic_entity_merge"] is False
    assert result["controls"]["automatic_claim_approval"] is False
    assert result["controls"]["automatic_export"] is False
    assert result["controls"]["automatic_publication"] is False


def test_v37_8_empty_workspace_is_safe(monkeypatch):
    monkeypatch.setattr(
        workspace,
        "build_guided_analyst_workflow",
        lambda: {"summary": {}, "findings": []},
    )
    monkeypatch.setattr(
        workspace,
        "build_relationship_chronology",
        lambda: {"summary": {}, "entries": []},
    )
    monkeypatch.setattr(workspace, "current_export_readiness_records", lambda: [])
    result = workspace.build_operational_case_intelligence_workspace()
    assert result["status"] == "ready"
    assert result["summary"]["chronology_entry_count"] == 0
    assert result["summary"]["export_readiness_record_count"] == 0
    assert result["summary"]["export_ready_count"] == 0
