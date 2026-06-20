from src.socmint.collaboration_workspace_v26_0 import build_collaboration_workspace


def _portfolio():
    return {
        "cases": [
            {
                "case_id": "case-a",
                "stage": "active",
                "status": "operational",
                "blocked": False,
                "blockers": [],
                "latest_activity_at": "2026-06-16T09:00:00+00:00",
            },
            {
                "case_id": "case-b",
                "stage": "closure_review",
                "status": "blocked",
                "blocked": True,
                "blockers": [{"key": "closure_review_required"}],
                "latest_activity_at": "2026-06-16T08:00:00+00:00",
            },
            {
                "case_id": "case-hidden",
                "stage": "active",
                "status": "operational",
                "blocked": False,
                "blockers": [],
                "latest_activity_at": "2026-06-16T07:00:00+00:00",
            },
        ]
    }


def _workload():
    return {
        "entries": [
            {
                "case_id": "case-a",
                "decision_record_id": 1,
                "actor": "analyst-a",
                "review_state": "unreviewed",
                "assigned_reviewer": "paul",
                "assigned_by": "supervisor-a",
                "assignment_age_hours": 5.0,
                "outstanding": True,
                "case_workspace_href": "/case-intelligence-review/case-a",
            },
            {
                "case_id": "case-b",
                "decision_record_id": 2,
                "actor": "paul",
                "review_state": "needs_follow_up",
                "assigned_reviewer": "reviewer-b",
                "assigned_by": "paul",
                "assignment_age_hours": 12.0,
                "outstanding": True,
                "case_workspace_href": "/case-intelligence-review/case-b",
            },
            {
                "case_id": "case-hidden",
                "decision_record_id": 3,
                "actor": "paul",
                "review_state": "unreviewed",
                "assigned_reviewer": "paul",
                "assigned_by": "supervisor-a",
                "assignment_age_hours": 1.0,
                "outstanding": True,
                "case_workspace_href": "/case-intelligence-review/case-hidden",
            },
        ]
    }


def _events():
    return [
        {
            "record_id": 10,
            "action": "case_team_role_assignment",
            "case_id": "case-a",
            "actor": "supervisor-a",
            "occurred_at": "2026-06-16T01:00:00+00:00",
            "details": {
                "case_team_assignment_id": "team-1",
                "user_identity": "paul",
                "role": "lead_analyst",
                "assignment_status": "active",
            },
        },
        {
            "record_id": 11,
            "action": "case_collaboration_request_created",
            "case_id": "case-a",
            "actor": "reviewer-b",
            "occurred_at": "2026-06-16T02:00:00+00:00",
            "details": {
                "collaboration_request_id": "request-1",
                "request_type": "evidence_review",
                "status": "requested",
                "requested_by": "reviewer-b",
                "requested_from": "paul",
                "priority": "high",
            },
        },
        {
            "record_id": 12,
            "action": "case_collaboration_handoff_created",
            "case_id": "case-b",
            "actor": "paul",
            "occurred_at": "2026-06-16T03:00:00+00:00",
            "details": {
                "collaboration_handoff_id": "handoff-1",
                "handoff_type": "case_ownership",
                "status": "pending",
                "handoff_from": "paul",
                "handoff_to": "reviewer-b",
            },
        },
        {
            "record_id": 13,
            "action": "case_collaboration_mention_created",
            "case_id": "case-a",
            "actor": "reviewer-b",
            "occurred_at": "2026-06-16T04:00:00+00:00",
            "details": {
                "mention_id": "mention-1",
                "mentioned_users": ["paul"],
                "status": "unread",
                "priority": "normal",
            },
        },
        {
            "record_id": 14,
            "action": "case_collaboration_request_created",
            "case_id": "case-hidden",
            "actor": "other",
            "occurred_at": "2026-06-16T05:00:00+00:00",
            "details": {
                "collaboration_request_id": "request-hidden",
                "status": "requested",
                "requested_from": "paul",
            },
        },
    ]


def test_v26_0_aggregates_participation_collaboration_and_actions():
    result = build_collaboration_workspace(
        "paul",
        allowed_case_ids={"case-a", "case-b"},
        portfolio=_portfolio(),
        workload=_workload(),
        collaboration_events=_events(),
    )

    assert result["status"] == "attention_required"
    assert result["access_scope"] == {
        "mode": "restricted",
        "allowed_case_ids": ["case-a", "case-b"],
    }
    assert result["counts"] == {
        "participating_cases": 2,
        "active_collaborators": 3,
        "pending_requests": 1,
        "pending_handoffs": 1,
        "unread_updates": 1,
        "unresolved_review_requests": 2,
        "blocked_collaboration_items": 2,
        "unresolved_collaboration_actions": 7,
    }
    cases = {item["case_id"]: item for item in result["participating_cases"]}
    assert set(cases) == {"case-a", "case-b"}
    assert {"lead_analyst", "reviewer", "participant"}.issubset(
        set(cases["case-a"]["assigned_roles"])
    )
    assert {"analyst", "supervisor", "participant"}.issubset(
        set(cases["case-b"]["assigned_roles"])
    )
    assert cases["case-a"]["links"]["evidence"] == "/dossier-assembly/case-a"
    assert cases["case-a"]["links"]["closure"] == "/case-closure/case-a"
    assert cases["case-a"]["links"]["archive"] == "/case-closure/case-a/history"
    assert cases["case-a"]["links"]["cross_case"] == "/cross-case-intelligence"
    assert result["pending_requests"][0]["collaboration_request_id"] == "request-1"
    assert result["pending_handoffs"][0]["collaboration_handoff_id"] == "handoff-1"
    assert result["unread_updates"][0]["collaboration_update_id"] == "mention-1"
    assert all(
        item.get("case_id") != "case-hidden"
        for item in result["unresolved_collaboration_actions"]
    )
    assert len(result["workspace_sha256"]) == 64
    assert result["read_only"] is True
    assert result["source_records_mutated"] is False
    assert result["collaboration_record_created"] is False
    assert result["access_granted_by_mention"] is False


def test_v26_0_empty_workspace_is_ready_and_deterministic():
    kwargs = {
        "allowed_case_ids": set(),
        "portfolio": {"cases": []},
        "workload": {"entries": []},
        "collaboration_events": [],
    }
    first = build_collaboration_workspace("paul", **kwargs)
    second = build_collaboration_workspace("paul", **kwargs)
    assert first["status"] == "ready"
    assert first["counts"]["participating_cases"] == 0
    assert first["workspace_sha256"] == second["workspace_sha256"]
