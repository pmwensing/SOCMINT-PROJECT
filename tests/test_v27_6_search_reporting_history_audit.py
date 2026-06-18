from src.socmint.search_reporting_history_audit_v27_6 import build_search_reporting_history_audit


def test_v27_6_consolidates_orders_counts_and_current_state(monkeypatch):
    from src.socmint import search_reporting_history_audit_v27_6 as audit
    monkeypatch.setattr(audit, "saved_view_history", lambda: [{"action_record_id":1,"recorded_by":"alice","recorded_at":"2026-06-17T01:00:00+00:00","source_action":"saved_search_view_created","event_type":"created","saved_view_id":"view-1","definition_sha256":"a"*64,"owner":"alice"}])
    monkeypatch.setattr(audit, "watchlist_history", lambda: [{"action_record_id":2,"recorded_by":"bob","recorded_at":"2026-06-17T02:00:00+00:00","source_action":"search_watchlist_run_recorded","event_type":"run","watchlist_id":"watch-1","monitoring_run_id":"run-1","result_count":2,"added_count":1,"removed_count":0,"result_set_sha256":"b"*64,"executed_access_scope":{"allowed_case_ids":["case-a"]},"owner":"bob"}])
    monkeypatch.setattr(audit, "report_history", lambda: [{"action_record_id":3,"recorded_by":"alice","recorded_at":"2026-06-17T03:00:00+00:00","source_action":"search_report_package_generated","event_type":"package_generated","report_id":"report-1","package_id":"package-1","section_count":2,"result_count":3,"package_sha256":"c"*64,"owner":"alice"}])
    monkeypatch.setattr(audit, "current_views", lambda: [{"view_status":"active"}])
    monkeypatch.setattr(audit, "current_watchlists", lambda: [{"watchlist_status":"active"}])
    monkeypatch.setattr(audit, "current_reports", lambda: [{"report_status":"active"}])
    monkeypatch.setattr(audit, "latest_packages", lambda: [{"package_id":"package-1"}])
    result = build_search_reporting_history_audit()
    assert result["status"] == "ready"
    assert [item["family"] for item in result["events"]] == ["saved_view","watchlist","report_package"]
    assert result["event_count"] == 3
    assert result["family_counts"] == {"report_package":1,"saved_view":1,"watchlist":1}
    assert result["current_state_counts"]["active_saved_view_count"] == 1
    assert result["current_state_counts"]["active_watchlist_count"] == 1
    assert result["current_state_counts"]["active_report_count"] == 1
    assert result["current_state_counts"]["report_package_count"] == 1
    assert all(len(item["raw_event_sha256"]) == 64 for item in result["events"])
    assert result["source_records_mutated"] is False
    assert result["history_events_mutated"] is False


def test_v27_6_filters_family_actor_and_limit(monkeypatch):
    from src.socmint import search_reporting_history_audit_v27_6 as audit
    monkeypatch.setattr(audit, "saved_view_history", lambda: [{"action_record_id":1,"recorded_by":"alice","recorded_at":"2026-06-17T01:00:00+00:00","source_action":"saved_search_view_created","event_type":"created"}])
    monkeypatch.setattr(audit, "watchlist_history", lambda: [{"action_record_id":2,"recorded_by":"bob","recorded_at":"2026-06-17T02:00:00+00:00","source_action":"search_watchlist_created","event_type":"created"}])
    monkeypatch.setattr(audit, "report_history", lambda: [])
    monkeypatch.setattr(audit, "current_views", lambda: [])
    monkeypatch.setattr(audit, "current_watchlists", lambda: [])
    monkeypatch.setattr(audit, "current_reports", lambda: [])
    monkeypatch.setattr(audit, "latest_packages", lambda: [])
    result = build_search_reporting_history_audit(families=["watchlist"], actors=["bob"], limit=1)
    assert result["event_count"] == 1
    assert result["events"][0]["actor"] == "bob"
    assert result["filters"] == {"families":["watchlist"],"actors":["bob"],"limit":1}
