from src.socmint import audience_package_authorization_panels_v33_3 as panels


def test_v33_3_builds_read_only_panels(monkeypatch):
    monkeypatch.setattr(
        panels,
        "build_case_governance_snapshot",
        lambda case_id: {
            "status": "attention_required",
            "case_id": case_id,
            "snapshot_sha256": "snapshot-sha-1",
            "current": {
                "audience_contract": {
                    "audience_contract_id": "audience-1",
                    "recipient_inventory": [{"recipient_id": "recipient-1"}],
                },
                "dissemination_package": {
                    "dissemination_package_id": "package-1"
                },
                "authorization_decision": None,
            },
            "blockers": [
                {
                    "key": "authorization_approval_required",
                    "stage": "authorization",
                }
            ],
        },
    )
    monkeypatch.setattr(
        panels,
        "build_case_action_queue",
        lambda case_id: {
            "queue_summary_sha256": "queue-sha-1",
            "next_action": "record_authorization_policy_decision",
            "action_queue": [
                {
                    "action": "record_authorization_policy_decision",
                    "stage": "authorization",
                    "delegate_service": "v32.service",
                    "confirmation_required": True,
                }
            ],
        },
    )
    monkeypatch.setattr(
        panels,
        "audience_contract_history",
        lambda: [{"case_id": "case-1", "audience_contract_id": "audience-1"}],
    )
    monkeypatch.setattr(
        panels,
        "dissemination_package_history",
        lambda: [{"case_id": "case-1", "dissemination_package_id": "package-1"}],
    )
    monkeypatch.setattr(panels, "authorization_decision_history", lambda: [])

    result = panels.build_case_audience_package_authorization_panels("case-1")

    assert result["status"] == "attention_required"
    assert result["panel_order"] == ["audience", "package", "authorization"]
    assert result["panels"]["audience"]["state"]["recipient_count"] == 1
    assert result["panels"]["package"]["state"]["assembled"] is True
    authorization = result["panels"]["authorization"]
    assert authorization["blockers"][0]["key"] == "authorization_approval_required"
    assert authorization["available_actions"][0]["action"] == (
        "record_authorization_policy_decision"
    )
    assert result["read_only"] is True
    assert result["actions_executed"] is False
    assert result["panels_sha256"]


def test_v33_3_sanitizes_sensitive_values(monkeypatch):
    monkeypatch.setattr(
        panels,
        "build_case_governance_snapshot",
        lambda case_id: {
            "status": "ready",
            "case_id": case_id,
            "snapshot_sha256": "snapshot-sha-1",
            "current": {
                "audience_contract": {
                    "audience_contract_id": "audience-1",
                    "endpoint_reference": "secret-value",
                },
                "dissemination_package": None,
                "authorization_decision": None,
            },
            "blockers": [],
        },
    )
    monkeypatch.setattr(
        panels,
        "build_case_action_queue",
        lambda case_id: {
            "queue_summary_sha256": "queue-sha-1",
            "next_action": "review_case_governance",
            "action_queue": [],
        },
    )
    monkeypatch.setattr(
        panels,
        "audience_contract_history",
        lambda: [
            {
                "case_id": "case-1",
                "audience_contract_id": "audience-1",
                "contact_secret": "hidden",
            }
        ],
    )
    monkeypatch.setattr(panels, "dissemination_package_history", lambda: [])
    monkeypatch.setattr(panels, "authorization_decision_history", lambda: [])

    result = panels.build_case_governance_panel("case-1", "audience")

    assert "endpoint_reference" not in result["current"]
    assert "contact_secret" not in result["history"][0]
    assert result["sensitive_values_rendered"] is False


def test_v33_3_blocks_invalid_panel(monkeypatch):
    monkeypatch.setattr(
        panels,
        "build_case_audience_package_authorization_panels",
        lambda case_id: {
            "status": "ready",
            "case_id": case_id,
            "snapshot_sha256": "snapshot-sha-1",
            "queue_summary_sha256": "queue-sha-1",
            "panels": {},
        },
    )

    result = panels.build_case_governance_panel("case-1", "unknown")

    assert result["status"] == "blocked"
    assert result["blockers"][0]["key"] == "invalid_panel"
