from src.socmint import action_queue_blocker_surface_v33_2 as queue


def test_v33_2_builds_prioritized_read_only_action_queue(monkeypatch):
    monkeypatch.setattr(
        queue,
        "build_case_governance_snapshot",
        lambda case_id: {
            "status": "attention_required",
            "case_id": case_id,
            "snapshot_sha256": "snapshot-sha-1",
            "blockers": [
                {"key": "authorization_approval_required", "stage": "authorization"},
                {"key": "retention_decision_required", "stage": "retention"},
            ],
            "safe_next_actions": [
                "record_authorization_policy_decision",
                "record_retention_decision",
            ],
            "current": {
                "dissemination_package": {
                    "dissemination_package_id": "package-1"
                }
            },
            "state": {},
        },
    )

    result = queue.build_case_action_queue("case-1")

    assert result["status"] == "attention_required"
    assert result["queue_count"] == 2
    assert result["critical_count"] == 1
    assert result["next_action"] == "record_authorization_policy_decision"
    assert [item["priority"] for item in result["action_queue"]] == [30, 80]
    first = result["action_queue"][0]
    assert first["stage"] == "authorization"
    assert first["targets"]["dissemination_package_id"] == "package-1"
    assert first["confirmation_required"] is True
    assert first["automatic_execution_allowed"] is False
    assert first["action_queue_item_sha256"]
    assert result["read_only"] is True
    assert result["actions_executed"] is False
    assert result["source_records_mutated"] is False


def test_v33_2_returns_ready_empty_queue(monkeypatch):
    monkeypatch.setattr(
        queue,
        "build_case_governance_snapshot",
        lambda case_id: {
            "status": "ready",
            "case_id": case_id,
            "snapshot_sha256": "snapshot-sha-1",
            "blockers": [],
            "safe_next_actions": [],
            "current": {},
            "state": {},
        },
    )

    result = queue.build_case_action_queue("case-1")

    assert result["status"] == "ready"
    assert result["action_queue"] == []
    assert result["next_action"] == "review_case_governance"
    assert result["decision_support_only"] is True


def test_v33_2_preserves_snapshot_blocked_state(monkeypatch):
    monkeypatch.setattr(
        queue,
        "build_case_governance_snapshot",
        lambda case_id: {
            "status": "blocked",
            "case_id": "",
            "blockers": [{"key": "case_id_required", "stage": "case"}],
        },
    )

    result = queue.build_case_action_queue("")

    assert result["status"] == "blocked"
    assert result["action_queue"] == []
    assert result["actions_executed"] is False
