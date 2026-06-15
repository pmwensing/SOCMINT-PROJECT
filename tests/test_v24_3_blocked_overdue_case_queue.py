from src.socmint import portfolio_blocked_overdue_queue_v24_3 as service


def test_v24_3_prioritizes_blocked_and_overdue_cases(monkeypatch):
    monkeypatch.setenv("SOCMINT_STAGE_OVERDUE_HOURS", "72")
    monkeypatch.setenv("SOCMINT_ASSIGNMENT_OVERDUE_HOURS", "48")
    monkeypatch.setattr(service, "build_portfolio_operations_dashboard", lambda: {
        "cases": [
            {
                "case_id": "case-critical",
                "stage": "closure_review",
                "blocked": True,
                "blockers": [{"key": "delivery_acknowledgement_required"}],
                "latest_actor": "owner-a",
                "links": {"case_review": "/case-intelligence-review/case-critical", "dossier_assembly": "/dossier-assembly/case-critical", "closure_workspace": "/case-closure/case-critical", "closure_history": "/case-closure/case-critical/history"},
            },
            {
                "case_id": "case-medium",
                "stage": "active",
                "blocked": False,
                "blockers": [],
                "latest_actor": "owner-b",
                "links": {"case_review": "/case-intelligence-review/case-medium", "dossier_assembly": "/dossier-assembly/case-medium", "closure_workspace": "/case-closure/case-medium", "closure_history": "/case-closure/case-medium/history"},
            },
        ]
    })
    monkeypatch.setattr(service, "build_case_status_stage_overview", lambda: {
        "cases": [
            {"case_id": "case-critical", "current_stage": "closure_review", "stage_duration_hours": 160.0, "blocked": True, "blocking_reason": "delivery_acknowledgement_required", "blockers": [{"key": "delivery_acknowledgement_required"}], "next_expected_action": "resolve_blocking_reason"},
            {"case_id": "case-medium", "current_stage": "active", "stage_duration_hours": 80.0, "blocked": False, "blocking_reason": None, "blockers": [], "next_expected_action": "complete_case_analysis"},
        ]
    })
    monkeypatch.setattr(service, "build_workload_assignment_monitoring", lambda: {
        "entries": [
            {"case_id": "case-critical", "review_state": "unreviewed", "assigned_reviewer": "alice", "assignment_age_hours": 100.0},
            {"case_id": "case-medium", "review_state": "unreviewed", "assigned_reviewer": "bob", "assignment_age_hours": 10.0},
        ]
    })

    result = service.build_blocked_overdue_case_queue()

    assert result["status"] == "attention_required"
    assert result["counts"]["total"] == 2
    assert result["counts"]["critical"] == 1
    assert result["counts"]["stage_overdue"] == 2
    assert result["counts"]["assignment_overdue"] == 1
    assert result["queue"][0]["case_id"] == "case-critical"
    assert result["queue"][0]["severity"] == "critical"
    assert result["queue"][0]["owner"] == "owner-a"
    assert result["queue"][0]["assigned_reviewers"] == ["alice"]
    assert result["queue"][0]["blocking_reason"] == "delivery_acknowledgement_required"
    assert result["queue"][0]["remediation_links"]["supervisor_queue"].endswith("case_id=case-critical")
    assert result["queue"][1]["severity"] == "medium"
    assert result["source_records_mutated"] is False
    assert result["queue_record_created"] is False


def test_v24_3_clear_queue_and_threshold_fallback(monkeypatch):
    monkeypatch.setenv("SOCMINT_STAGE_OVERDUE_HOURS", "bad")
    monkeypatch.setenv("SOCMINT_ASSIGNMENT_OVERDUE_HOURS", "bad")
    monkeypatch.setattr(service, "build_portfolio_operations_dashboard", lambda: {"cases": []})
    monkeypatch.setattr(service, "build_case_status_stage_overview", lambda: {"cases": []})
    monkeypatch.setattr(service, "build_workload_assignment_monitoring", lambda: {"entries": []})

    result = service.build_blocked_overdue_case_queue()
    assert result["status"] == "clear"
    assert result["thresholds"]["stage_overdue_hours"] == 72.0
    assert result["thresholds"]["assignment_overdue_hours"] == 48.0
    assert result["queue"] == []
    assert result["next_action"] == "monitor_portfolio"
