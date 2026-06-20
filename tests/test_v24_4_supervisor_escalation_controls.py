from src.socmint import database
from src.socmint import portfolio_supervisor_escalation_v24_4 as service


def _queue():
    return {
        "schema": "socmint.portfolio_blocked_overdue_queue.v24_3",
        "version": "v24.3.0",
        "thresholds": {"stage_overdue_hours": 72.0, "assignment_overdue_hours": 48.0},
        "queue": [
            {
                "case_id": "case-alpha",
                "severity": "critical",
                "severity_rank": 4,
                "current_stage": "closure_review",
                "stage_age_hours": 160.0,
                "stage_overdue": True,
                "stage_overdue_by_hours": 88.0,
                "assignment_age_hours": 100.0,
                "assignment_overdue": True,
                "assignment_overdue_by_hours": 52.0,
                "blocked": True,
                "blocking_reason": "delivery_acknowledgement_required",
                "blockers": [{"key": "delivery_acknowledgement_required"}],
                "owner": "owner-a",
                "assigned_reviewers": ["alice"],
                "active_assignment_count": 1,
                "review_states": ["unreviewed"],
                "next_expected_action": "resolve_blocking_reason",
                "remediation_links": {
                    "case_review": "/case-intelligence-review/case-alpha"
                },
            }
        ],
    }


def _setup(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'app.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    database.configure_database(url)
    monkeypatch.setattr(service, "build_blocked_overdue_case_queue", _queue)


def test_v24_4_records_bound_immutable_control_events(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)

    escalated = service.record_escalation(
        "case-alpha",
        confirmed=True,
        supervisor="supervisor",
        reason="Critical blocker exceeded thresholds.",
        note="Immediate review.",
    )
    acknowledged = service.acknowledge_escalation(
        "case-alpha", confirmed=True, supervisor="supervisor", note="Acknowledged."
    )
    reassigned = service.reassign_escalation(
        "case-alpha",
        confirmed=True,
        supervisor="supervisor",
        assigned_reviewer="bob",
        note="Move to available reviewer.",
    )
    resolved = service.resolve_escalation(
        "case-alpha",
        confirmed=True,
        supervisor="supervisor",
        resolution="Blocker remediated and follow-up scheduled.",
        note="Resolved.",
    )
    history = service.escalation_history("case-alpha")

    assert escalated["status"] == "escalate_recorded"
    assert escalated["source_state"]["queue_item"]["severity"] == "critical"
    assert escalated["source_state_sha256"]
    assert acknowledged["status"] == "acknowledge_recorded"
    assert (
        acknowledged["payload"]["escalation_event_id"] == escalated["control_event_id"]
    )
    assert reassigned["payload"]["assigned_reviewer"] == "bob"
    assert resolved["payload"]["resolution"].startswith("Blocker remediated")
    assert [item["control"] for item in history] == [
        "escalate",
        "acknowledge",
        "reassign",
        "resolve",
    ]
    for result in (escalated, acknowledged, reassigned, resolved):
        assert result["source_records_mutated"] is False
        assert result["case_events_mutated"] is False
        assert result["stage_events_mutated"] is False
        assert result["assignment_events_mutated"] is False
        assert result["queue_snapshot_mutated"] is False


def test_v24_4_enforces_confirmation_source_and_required_values(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    assert (
        service.record_escalation(
            "case-alpha", confirmed=False, supervisor="supervisor", reason="reason"
        )["blockers"][0]["key"]
        == "explicit_escalation_confirmation_required"
    )
    assert (
        service.record_escalation(
            "case-alpha", confirmed=True, supervisor="supervisor", reason=""
        )["blockers"][0]["key"]
        == "escalation_reason_required"
    )
    assert (
        service.acknowledge_escalation(
            "case-alpha", confirmed=True, supervisor="supervisor"
        )["blockers"][0]["key"]
        == "escalation_required"
    )

    monkeypatch.setattr(
        service, "build_blocked_overdue_case_queue", lambda: {"queue": []}
    )
    blocked = service.record_escalation(
        "case-alpha", confirmed=True, supervisor="supervisor", reason="reason"
    )
    assert blocked["blockers"][0]["key"] == "blocked_or_overdue_queue_item_required"
