from src.socmint import database
from src.socmint.dossier_assembly_workspace_v21_0 import _canonical, _ensure_storage
from src.socmint.dossier_release_history_v22_6 import build_release_delivery_history


def _setup(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'app.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    database.configure_database(url)
    _ensure_storage()


def _event(case_id, actor, action, details):
    session = database.Session()
    try:
        session.add(database.AuditLog(
            actor=actor,
            action=action,
            target_value=case_id,
            details=_canonical(details),
        ))
        session.commit()
    finally:
        session.close()


def test_v22_6_consolidates_ordered_history_and_unresolved_actions(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    _event("case-alpha", "operator", "case_dossier_release_authorization", {
        "authorization_id": "auth-1",
    })
    _event("case-alpha", "operator", "case_dossier_release_preview", {
        "preview_id": "preview-1",
    })
    _event("case-alpha", "operator", "case_dossier_secure_distribution", {
        "distribution_id": "distribution-1",
        "status": "dispatch_recorded",
    })
    _event("case-alpha", "operator", "case_dossier_delivery_receipt", {
        "delivery_receipt_id": "receipt-1",
        "delivery_result": "delivered",
    })

    result = build_release_delivery_history("case-alpha")
    assert [item["event_type"] for item in result["timeline"]] == [
        "authorization", "preview", "dispatch", "delivery_receipt"
    ]
    assert result["current_release_outcome"] == "delivered_acknowledgement_pending"
    assert result["closure_ready"] is False
    assert result["unresolved_actions"] == [
        {"key": "recipient_acknowledgement_outstanding"}
    ]
    assert result["source_records_mutated"] is False


def test_v22_6_produces_closure_ready_summary(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    events = [
        ("case_dossier_release_authorization", {"authorization_id": "auth-1"}),
        ("case_dossier_secure_distribution", {"distribution_id": "distribution-1", "status": "dispatch_recorded"}),
        ("case_dossier_delivery_receipt", {"delivery_receipt_id": "receipt-1", "delivery_result": "delivered"}),
        ("case_dossier_recipient_acknowledgement", {"acknowledgement_id": "ack-1", "recipient_acknowledged": True}),
    ]
    for action, details in events:
        _event("case-alpha", "operator", action, details)

    result = build_release_delivery_history("case-alpha")
    assert result["status"] == "closure_ready"
    assert result["current_release_outcome"] == "delivered_and_acknowledged"
    assert result["closure_ready"] is True
    assert result["unresolved_action_count"] == 0
    assert result["closure_summary"]["authorization_id"] == "auth-1"
    assert result["closure_summary"]["distribution_id"] == "distribution-1"
    assert result["closure_summary"]["delivery_receipt_id"] == "receipt-1"
    assert result["closure_summary"]["acknowledgement_id"] == "ack-1"
    assert result["next_action"] == "close_release_case"
