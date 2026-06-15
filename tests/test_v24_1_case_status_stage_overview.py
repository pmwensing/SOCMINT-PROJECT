import datetime as dt

from src.socmint import portfolio_case_stage_overview_v24_1 as service


def test_v24_1_normalizes_stage_progress_and_duration():
    events = [
        {"record_id": 1, "action": "dossier_final_export_package", "occurred_at": "2026-06-15T10:00:00+00:00", "details": {}},
        {"record_id": 2, "action": "dossier_delivery_receipt", "occurred_at": "2026-06-15T11:00:00+00:00", "details": {}},
        {"record_id": 3, "action": "case_supervisor_closure_decision", "occurred_at": "2026-06-15T12:00:00+00:00", "details": {"decision": "close"}},
        {"record_id": 4, "action": "case_retention_policy_assignment", "occurred_at": "2026-06-15T13:00:00+00:00", "details": {}},
        {"record_id": 5, "action": "case_archive_package_generated", "occurred_at": "2026-06-15T14:00:00+00:00", "details": {}},
    ]
    result = service.normalize_case_stage(
        "case-alpha",
        events,
        now=dt.datetime(2026, 6, 15, 16, 30, tzinfo=dt.UTC),
    )

    assert result["current_stage"] == "archived"
    assert result["prior_stage"] == "retention_pending_archive"
    assert result["stage_entered_at"] == "2026-06-15T14:00:00+00:00"
    assert result["stage_duration_seconds"] == 9000
    assert result["stage_duration_hours"] == 2.5
    assert result["progress_position"] == 8
    assert result["progress_total"] == 9
    assert result["progress_percent"] == 88.9
    assert result["blocking_reason"] is None
    assert result["next_expected_action"] == "monitor_retention_or_request_reopen"


def test_v24_1_exposes_blocking_reason_and_overview(monkeypatch):
    monkeypatch.setattr(service, "_configured_case_ids", lambda: ["case-unstarted"])
    monkeypatch.setattr(service, "_case_events", lambda: {
        "case-blocked": [{
            "record_id": 1,
            "action": "case_closure_readiness_review",
            "occurred_at": "2026-06-15T10:00:00+00:00",
            "details": {"blockers": [{"key": "delivery_acknowledgement_required"}]},
        }]
    })
    result = service.build_case_status_stage_overview(
        now=dt.datetime(2026, 6, 15, 12, 0, tzinfo=dt.UTC)
    )
    by_case = {item["case_id"]: item for item in result["cases"]}

    assert result["case_count"] == 2
    assert result["blocked_count"] == 1
    assert by_case["case-blocked"]["current_stage"] == "closure_review"
    assert by_case["case-blocked"]["blocking_reason"] == "delivery_acknowledgement_required"
    assert by_case["case-blocked"]["next_expected_action"] == "resolve_blocking_reason"
    assert by_case["case-unstarted"]["current_stage"] == "unstarted"
    assert by_case["case-unstarted"]["next_expected_action"] == "begin_case_review"
    assert result["source_records_mutated"] is False
    assert result["stage_record_created"] is False
