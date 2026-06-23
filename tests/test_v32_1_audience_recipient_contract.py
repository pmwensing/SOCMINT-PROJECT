from src.socmint import audience_recipient_contract_v32_1 as contracts


RECIPIENTS = [
    {
        "recipient_id": "recipient-1",
        "display_name": "Review Team",
        "organization": "Example Agency",
        "role": "reviewer",
        "recipient_type": "team",
        "dissemination_purpose": "case review",
        "max_classification": "restricted",
        "allowed_channels": ["secure_portal"],
    }
]


def test_v32_1_records_proposed_contract_without_authorizing_delivery(monkeypatch):
    monkeypatch.setattr(contracts, "audience_contract_history", lambda: [])
    monkeypatch.setattr(
        contracts,
        "_record",
        lambda actor, target_value, event, ip_address: {
            **event,
            "recorded_by": actor,
        },
    )

    result = contracts.record_audience_recipient_contract(
        actor="admin",
        case_id="case-1",
        audience_name="Restricted Review Audience",
        audience_type="regulatory",
        dissemination_purpose="case review",
        classification="restricted",
        recipients=RECIPIENTS,
        reason="operator request",
        confirmed=True,
    )

    assert result["status"] == "audience_contract_recorded"
    assert result["contract_state"] == "proposed"
    assert result["authorization_state"] == "not_authorized"
    assert result["authorization_granted"] is False
    assert result["package_assembly_performed"] is False
    assert result["transmission_performed"] is False
    assert result["contact_secret_stored"] is False
    assert result["audience_contract_id"].startswith("audience-contract-")
    assert result["recipient_inventory"]["recipient_count"] == 1


def test_v32_1_blocks_recipient_below_audience_classification(monkeypatch):
    monkeypatch.setattr(contracts, "audience_contract_history", lambda: [])
    recipient = {**RECIPIENTS[0], "max_classification": "internal"}

    result = contracts.record_audience_recipient_contract(
        actor="admin",
        case_id="case-1",
        audience_name="Restricted Review Audience",
        audience_type="regulatory",
        dissemination_purpose="case review",
        classification="restricted",
        recipients=[recipient],
        reason="operator request",
        confirmed=True,
    )

    assert result["status"] == "blocked"
    assert result["blockers"][0]["key"] == "recipient_classification_insufficient"
    assert result["authorization_granted"] is False


def test_v32_1_blocks_duplicate_recipient_ids(monkeypatch):
    monkeypatch.setattr(contracts, "audience_contract_history", lambda: [])

    result = contracts.record_audience_recipient_contract(
        actor="admin",
        case_id="case-1",
        audience_name="Internal Review Audience",
        audience_type="internal",
        dissemination_purpose="case review",
        classification="internal",
        recipients=[RECIPIENTS[0], dict(RECIPIENTS[0])],
        reason="operator request",
        confirmed=True,
    )

    assert result["status"] == "blocked"
    assert result["blockers"][0]["key"] == "duplicate_recipient_id"


def test_v32_1_requires_explicit_confirmation():
    result = contracts.record_audience_recipient_contract(
        actor="admin",
        case_id="case-1",
        audience_name="Internal Review Audience",
        audience_type="internal",
        dissemination_purpose="case review",
        classification="internal",
        recipients=RECIPIENTS,
        reason="operator request",
        confirmed=False,
    )

    assert result["status"] == "blocked"
    assert result["blockers"][0]["key"] == "explicit_contract_confirmation_required"
