from src.socmint import database
from src.socmint import dossier_delivery_receipt_v22_4 as service


def _distribution():
    return {
        "status": "dispatch_recorded",
        "distribution_id": "secure-distribution-1",
        "distribution_record_id": 51,
        "dispatch_request_sha256": "a" * 64,
        "dispatch_request": {
            "export_package_id": "dossier-export-1",
            "recipient_id": "recipient-1",
            "delivery_channel": "secure_portal",
        },
    }


def _setup(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'app.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    database.configure_database(url)
    monkeypatch.setattr(service, "latest_secure_distribution", lambda case_id: _distribution())


def test_v22_4_records_success_and_outstanding_acknowledgement(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    receipt = service.record_delivery_receipt(
        "case-alpha",
        delivery_result="delivered",
        recorder="operator",
        provider_message_id="provider-123",
        transport_status="accepted",
        delivered_at="2026-06-14T04:45:00Z",
        note="Delivery confirmed.",
    )
    state = service.build_delivery_receipt_state("case-alpha")
    assert receipt["status"] == "delivery_recorded"
    assert receipt["acknowledgement_required"] is True
    assert receipt["dispatch_record_mutated"] is False
    assert state["delivery_succeeded"] is True
    assert state["acknowledgement_outstanding"] is True
    assert state["acknowledgement_received"] is False
    assert state["next_action"] == "record_recipient_acknowledgement"


def test_v22_4_failure_and_separate_recipient_acknowledgement(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    failed = service.record_delivery_receipt(
        "case-alpha",
        delivery_result="failed",
        recorder="operator",
        failure_code="recipient_unavailable",
        failure_detail="Recipient endpoint rejected the delivery.",
    )
    assert failed["delivery_result"] == "failed"
    assert failed["next_action"] == "review_delivery_failure"

    delivered = service.record_delivery_receipt(
        "case-alpha",
        delivery_result="delivered",
        recorder="operator",
        provider_message_id="provider-456",
    )
    blocked = service.record_recipient_acknowledgement(
        "case-alpha", acknowledged=False, recorder="operator"
    )
    assert blocked["blockers"][0]["key"] == "explicit_recipient_acknowledgement_required"

    ack = service.record_recipient_acknowledgement(
        "case-alpha",
        acknowledged=True,
        recorder="operator",
        recipient_name="Authorized Recipient",
        acknowledgement_method="secure_portal_confirmation",
        acknowledged_at="2026-06-14T04:50:00Z",
        note="Recipient confirmed access.",
    )
    state = service.build_delivery_receipt_state("case-alpha")
    assert ack["status"] == "acknowledgement_recorded"
    assert ack["delivery_receipt_id"] == delivered["delivery_receipt_id"]
    assert ack["dispatch_record_mutated"] is False
    assert ack["delivery_receipt_mutated"] is False
    assert state["acknowledgement_received"] is True
    assert state["acknowledgement_outstanding"] is False
    assert state["next_action"] == "delivery_handoff_complete"
