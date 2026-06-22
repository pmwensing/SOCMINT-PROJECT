from src.socmint import delivery_attempt_receipt_ledger_v32_4 as ledger


PACKAGE = {
    "case_id": "case-1",
    "dissemination_package_id": "package-1",
    "dissemination_package_sha256": "package-sha-1",
    "package_manifest": {
        "recipients": [
            {
                "recipient_id": "recipient-1",
                "allowed_channels": ["secure_portal"],
            }
        ]
    },
}

APPROVAL = {
    "authorization_decision_id": "authorization-1",
    "authorization_decision_sha256": "authorization-sha-1",
    "dissemination_package_sha256": "package-sha-1",
    "result_status": "approved_for_delivery_attempt",
}


def test_v32_4_records_attempt_without_storing_endpoint_secret(monkeypatch):
    monkeypatch.setattr(ledger, "find_dissemination_package", lambda package_id: PACKAGE)
    monkeypatch.setattr(ledger, "latest_approved_decision", lambda package_id: APPROVAL)
    monkeypatch.setattr(ledger, "delivery_attempt_history", lambda: [])
    monkeypatch.setattr(
        ledger,
        "_record",
        lambda **kwargs: {**kwargs["event"], "recorded_by": kwargs["actor"]},
    )

    result = ledger.record_delivery_attempt(
        operator="admin",
        dissemination_package_id="package-1",
        recipient_id="recipient-1",
        delivery_channel="secure_portal",
        endpoint_reference="opaque-endpoint-token",
        attempt_result="accepted",
        transport_reference="transport-1",
        reason="authorized delivery",
        confirmed=True,
    )

    assert result["status"] == "delivery_attempt_recorded"
    assert result["contact_secret_stored"] is False
    assert "endpoint_reference" not in result
    assert result["endpoint_reference_sha256"]
    assert result["transport_invoked_by_ledger"] is False
    assert result["prior_attempt_mutated"] is False


def test_v32_4_blocks_attempt_without_approval(monkeypatch):
    monkeypatch.setattr(ledger, "find_dissemination_package", lambda package_id: PACKAGE)
    monkeypatch.setattr(ledger, "latest_approved_decision", lambda package_id: None)

    result = ledger.record_delivery_attempt(
        operator="admin",
        dissemination_package_id="package-1",
        recipient_id="recipient-1",
        delivery_channel="secure_portal",
        endpoint_reference="opaque-endpoint-token",
        attempt_result="accepted",
        transport_reference="transport-1",
        reason="authorized delivery",
        confirmed=True,
    )

    assert result["status"] == "blocked"
    assert result["blockers"][0]["key"] == "approved_authorization_decision_required"


def test_v32_4_records_delivery_receipt_append_only(monkeypatch):
    attempt = {
        "case_id": "case-1",
        "delivery_attempt_id": "attempt-1",
        "delivery_attempt_sha256": "attempt-sha-1",
        "dissemination_package_id": "package-1",
        "authorization_decision_id": "authorization-1",
        "recipient_id": "recipient-1",
        "delivery_channel": "secure_portal",
        "attempt_result": "accepted",
    }
    monkeypatch.setattr(ledger, "find_delivery_attempt", lambda attempt_id: attempt)
    monkeypatch.setattr(ledger, "delivery_receipt_history", lambda: [])
    monkeypatch.setattr(
        ledger,
        "_record",
        lambda **kwargs: kwargs["event"],
    )

    result = ledger.record_delivery_receipt(
        recorder="admin",
        delivery_attempt_id="attempt-1",
        delivery_result="delivered",
        provider_message_id="provider-1",
        transport_status="completed",
        delivered_at="2026-06-22T12:00:00Z",
        confirmed=True,
    )

    assert result["status"] == "delivery_receipt_recorded"
    assert result["acknowledgement_required"] is True
    assert result["prior_attempt_mutated"] is False
    assert result["prior_receipt_mutated"] is False
