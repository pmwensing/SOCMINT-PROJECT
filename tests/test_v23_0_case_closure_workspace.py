from src.socmint import case_closure_workspace_v23_0 as service


def test_v23_0_builds_eligible_closure_workspace(monkeypatch):
    monkeypatch.setattr(service, "build_release_delivery_history", lambda case_id: {
        "case_id": case_id,
        "closure_ready": True,
        "current_release_outcome": "delivered_and_acknowledged",
        "unresolved_actions": [],
        "closure_summary": {"case_id": case_id, "closure_ready": True},
    })
    monkeypatch.setattr(service, "build_delivery_recovery_state", lambda case_id: {
        "case_id": case_id,
        "delivery_failed": False,
        "delivery_succeeded": True,
        "acknowledgement_received": True,
        "failed_delivery_review_required": False,
        "latest_recall_request": None,
        "latest_reissue_authorization": None,
        "next_action": "monitor_delivery_recovery",
    })

    result = service.build_case_closure_workspace("case-alpha")
    assert result["status"] == "eligible_for_closure_review"
    assert result["closure_eligible"] is True
    assert result["archive_ready"] is True
    assert result["blocker_count"] == 0
    assert result["proposed_retention_policy"]["policy_id"] == "standard_case_retention"
    assert result["source_records_mutated"] is False
    assert result["closure_record_created"] is False
    assert result["retention_assignment_created"] is False
    assert result["archive_package_created"] is False
    assert result["next_action"] == "review_closure_readiness"


def test_v23_0_exposes_closure_blockers(monkeypatch):
    monkeypatch.setattr(service, "build_release_delivery_history", lambda case_id: {
        "case_id": case_id,
        "closure_ready": False,
        "current_release_outcome": "delivery_failed",
        "unresolved_actions": [{"key": "failed_delivery_review_outstanding"}],
        "closure_summary": {"case_id": case_id, "closure_ready": False},
    })
    monkeypatch.setattr(service, "build_delivery_recovery_state", lambda case_id: {
        "case_id": case_id,
        "delivery_failed": True,
        "delivery_succeeded": False,
        "acknowledgement_received": False,
        "failed_delivery_review_required": True,
        "latest_recall_request": {"recall_request_id": "recall-1"},
        "latest_reissue_authorization": None,
        "next_action": "review_failed_delivery",
    })

    result = service.build_case_closure_workspace("case-alpha")
    keys = {item["key"] for item in result["blockers"]}
    assert result["status"] == "blocked"
    assert result["closure_eligible"] is False
    assert result["archive_ready"] is False
    assert "failed_delivery_review_outstanding" in keys
    assert "release_closure_readiness_required" in keys
    assert "failed_delivery_review_required" in keys
    assert "recall_or_reissue_resolution_required" in keys
