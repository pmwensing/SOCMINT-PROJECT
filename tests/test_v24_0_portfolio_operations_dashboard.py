from src.socmint import portfolio_operations_dashboard_v24_0 as service


def test_v24_0_builds_portfolio_counts_and_case_links(monkeypatch):
    monkeypatch.setattr(service, "_configured_case_ids", lambda: ["case-unstarted"])
    monkeypatch.setattr(
        service,
        "_case_events",
        lambda: {
            "case-active": [
                {
                    "record_id": 1,
                    "action": "case_closure_readiness_review",
                    "actor": "reviewer",
                    "occurred_at": "2026-06-15T01:00:00",
                    "details": {"status": "review_recorded"},
                }
            ],
            "case-archived": [
                {
                    "record_id": 2,
                    "action": "case_archive_package_generated",
                    "actor": "supervisor",
                    "occurred_at": "2026-06-15T02:00:00",
                    "details": {"status": "archive_package_generated"},
                }
            ],
            "case-reopened": [
                {
                    "record_id": 3,
                    "action": "case_archive_package_generated",
                    "actor": "supervisor",
                    "occurred_at": "2026-06-15T03:00:00",
                    "details": {},
                },
                {
                    "record_id": 4,
                    "action": "case_reopen_authorization",
                    "actor": "supervisor",
                    "occurred_at": "2026-06-15T04:00:00",
                    "details": {"decision": "authorize"},
                },
            ],
            "case-blocked": [
                {
                    "record_id": 5,
                    "action": "dossier_quality_review",
                    "actor": "operator",
                    "occurred_at": "2026-06-15T05:00:00",
                    "details": {
                        "status": "blocked",
                        "blockers": [{"key": "citation_required"}],
                    },
                }
            ],
        },
    )

    result = service.build_portfolio_operations_dashboard()
    by_case = {item["case_id"]: item for item in result["cases"]}

    assert result["status"] == "ready"
    assert result["counts"]["total"] == 5
    assert result["counts"]["archived"] == 1
    assert result["counts"]["reopened"] == 1
    assert result["counts"]["blocked"] == 1
    assert result["counts"]["unstarted"] == 1
    assert by_case["case-reopened"]["stage"] == "reopened"
    assert by_case["case-archived"]["stage"] == "archived"
    assert by_case["case-blocked"]["blocked"] is True
    assert by_case["case-blocked"]["blockers"][0]["key"] == "citation_required"
    assert (
        by_case["case-active"]["links"]["closure_workspace"]
        == "/case-closure/case-active"
    )
    assert result["source_records_mutated"] is False
    assert result["portfolio_record_created"] is False


def test_v24_0_stage_precedence(monkeypatch):
    events = [
        {
            "record_id": 1,
            "action": "dossier_delivery_receipt",
            "actor": "operator",
            "occurred_at": "2026-06-15T01:00:00",
            "details": {},
        },
        {
            "record_id": 2,
            "action": "case_supervisor_closure_decision",
            "actor": "supervisor",
            "occurred_at": "2026-06-15T02:00:00",
            "details": {"decision": "close"},
        },
        {
            "record_id": 3,
            "action": "case_archive_package_generated",
            "actor": "supervisor",
            "occurred_at": "2026-06-15T03:00:00",
            "details": {},
        },
        {
            "record_id": 4,
            "action": "case_reopen_authorization",
            "actor": "supervisor",
            "occurred_at": "2026-06-15T04:00:00",
            "details": {"decision": "authorize"},
        },
    ]
    case = service._derive_case("case-alpha", events)
    assert case["stage"] == "reopened"
    assert case["latest_action"] == "case_reopen_authorization"
