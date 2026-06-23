from src.socmint import case_centric_operator_workspace_v33_6 as workspace


def test_v33_6_composes_all_governance_sections(monkeypatch):
    monkeypatch.setattr(workspace, "build_case_governance_snapshot", lambda case_id: {"status": "ready", "case_id": case_id, "blockers": [], "next_action": "review"})
    monkeypatch.setattr(workspace, "build_case_action_queue", lambda case_id: {"action_queue": [], "next_action": "review"})
    monkeypatch.setattr(workspace, "build_case_audience_package_authorization_panels", lambda case_id: {"status": "ready", "panels": {}})
    monkeypatch.setattr(workspace, "build_case_delivery_receipt_feedback_panels", lambda case_id: {"status": "ready", "panels": {}})
    monkeypatch.setattr(workspace, "build_case_recall_retention_lifecycle_timeline", lambda case_id: {"status": "ready", "current_retention_state": "retained", "current_recall_states": {}})

    result = workspace.build_case_centric_operator_workspace("case-1")

    assert result["status"] == "ready"
    assert result["section_order"] == [
        "overview",
        "action_queue",
        "audience_package_authorization",
        "delivery_receipt_feedback",
        "recall_retention_lifecycle",
    ]
    assert result["summary"]["retention_state"] == "retained"
    assert result["workspace_sha256"]
    assert result["actions_executed"] is False
