from src.socmint import database
from src.socmint import dossier_delivery_recovery_controls_v22_5 as service


def _distribution():
    return {
        "status": "dispatch_recorded",
        "distribution_id": "secure-distribution-1",
        "dispatch_request_sha256": "a" * 64,
        "dispatch_request": {
            "export_package_id": "dossier-export-1",
            "recipient_id": "recipient-1",
            "delivery_channel": "secure_portal",
        },
    }


def _failed_receipt():
    return {
        "delivery_receipt_id": "delivery-receipt-1",
        "delivery_receipt_sha256": "b" * 64,
        "distribution_id": "secure-distribution-1",
        "export_package_id": "dossier-export-1",
        "recipient_id": "recipient-1",
        "delivery_result": "failed",
        "failure_code": "recipient_unavailable",
        "failure_detail": "Endpoint rejected delivery.",
    }


def _setup(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'app.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    database.configure_database(url)
    monkeypatch.setattr(service, "latest_secure_distribution", lambda case_id: _distribution())
    monkeypatch.setattr(service, "latest_delivery_receipt", lambda case_id: _failed_receipt())
    monkeypatch.setattr(service, "latest_recipient_acknowledgement", lambda case_id: None)


def test_v22_5_failed_delivery_review_and_recall(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    blocked = service.review_failed_delivery(
        "case-alpha",
        confirmed=False,
        reviewer="operator",
        root_cause="endpoint unavailable",
        resolution_plan="retry after confirmation",
    )
    assert blocked["blockers"][0]["key"] == "explicit_failed_delivery_review_confirmation_required"

    review = service.review_failed_delivery(
        "case-alpha",
        confirmed=True,
        reviewer="operator",
        root_cause="endpoint unavailable",
        resolution_plan="confirm recipient availability before reissue",
        note="Reviewed failure.",
    )
    recall = service.request_recall(
        "case-alpha",
        confirmed=True,
        requester="operator",
        reason="Withdraw failed delivery link.",
        scope="recipient_access",
    )
    assert review["status"] == "failed_delivery_review_recorded"
    assert review["dispatch_record_mutated"] is False
    assert review["delivery_receipt_mutated"] is False
    assert recall["status"] == "recall_requested"
    assert recall["dispatch_record_mutated"] is False
    assert recall["acknowledgement_record_mutated"] is False


def test_v22_5_reissue_tied_to_original_history(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    monkeypatch.setattr(service, "latest_recall_request", lambda case_id: {
        "recall_request_id": "recall-1",
    })
    result = service.authorize_reissue(
        "case-alpha",
        confirmed=True,
        authorizer="supervisor",
        target_recipient_id="recipient-2",
        target_delivery_channel="encrypted_email",
        reason="Recipient endpoint changed.",
        note="Reissue authorized.",
    )
    assert result["status"] == "reissue_authorized"
    assert result["authorized"] is True
    assert result["history"]["original_distribution_id"] == "secure-distribution-1"
    assert result["history"]["original_export_package_id"] == "dossier-export-1"
    assert result["history"]["original_recipient_id"] == "recipient-1"
    assert result["history"]["delivery_receipt_id"] == "delivery-receipt-1"
    assert result["history"]["recall_request_id"] == "recall-1"
    assert result["target_recipient_id"] == "recipient-2"
    assert result["dispatch_record_mutated"] is False
    assert result["delivery_receipt_mutated"] is False
    assert result["acknowledgement_record_mutated"] is False
