from src.socmint import case_governance_snapshot_v33_1 as snapshot


def _patch_histories(monkeypatch, *, populated: bool = True):
    case_id = "case-1"
    audience = [{"case_id": case_id, "audience_contract_id": "audience-1"}]
    package = [
        {
            "case_id": case_id,
            "dissemination_package_id": "package-1",
        }
    ]
    approval = [
        {
            "case_id": case_id,
            "authorization_decision_id": "authorization-1",
            "result_status": "approved_for_delivery_attempt",
        }
    ]
    attempt = [
        {
            "case_id": case_id,
            "delivery_attempt_id": "attempt-1",
        }
    ]
    receipt = [
        {
            "case_id": case_id,
            "delivery_receipt_id": "receipt-1",
            "delivery_result": "delivered",
        }
    ]
    rows = [audience, package, approval, attempt, receipt]
    if not populated:
        rows = [[] for _ in rows]

    monkeypatch.setattr(snapshot, "audience_contract_history", lambda: rows[0])
    monkeypatch.setattr(snapshot, "dissemination_package_history", lambda: rows[1])
    monkeypatch.setattr(snapshot, "authorization_decision_history", lambda: rows[2])
    monkeypatch.setattr(snapshot, "delivery_attempt_history", lambda: rows[3])
    monkeypatch.setattr(snapshot, "delivery_receipt_history", lambda: rows[4])
    monkeypatch.setattr(snapshot, "recipient_feedback_history", lambda: [])
    monkeypatch.setattr(snapshot, "correction_intake_history", lambda: [])
    monkeypatch.setattr(snapshot, "recall_decision_history", lambda: [])
    monkeypatch.setattr(
        snapshot,
        "retention_decision_history",
        lambda: ([{"case_id": case_id, "retention_decision_id": "retention-1"}] if populated else []),
    )
    monkeypatch.setattr(
        snapshot,
        "current_retention_state",
        lambda value: "retained" if populated else "unassigned",
    )
    monkeypatch.setattr(snapshot, "current_recall_state", lambda value: "not_recalled")
    monkeypatch.setattr(
        snapshot,
        "lifecycle_snapshot",
        lambda value: {"case_id": value, "event_count": 5 if populated else 0},
    )


def test_v33_1_builds_ready_case_scoped_read_model(monkeypatch):
    _patch_histories(monkeypatch)

    result = snapshot.build_case_governance_snapshot("case-1")

    assert result["status"] == "ready"
    assert result["case_id"] == "case-1"
    assert result["counts"]["audience_contracts"] == 1
    assert result["counts"]["delivered_receipts"] == 1
    assert result["blockers"] == []
    assert result["safe_next_actions"] == []
    assert result["read_only"] is True
    assert result["canonical_browser_api_read_model"] is True
    assert result["v32_contracts_remain_authoritative"] is True
    assert result["source_records_mutated"] is False
    assert result["raw_endpoint_or_contact_secret_rendered"] is False
    assert result["snapshot_sha256"]


def test_v33_1_exposes_ordered_blockers_and_safe_actions(monkeypatch):
    _patch_histories(monkeypatch, populated=False)

    result = snapshot.build_case_governance_snapshot("case-1")

    assert result["status"] == "attention_required"
    assert [item["key"] for item in result["blockers"]] == [
        "audience_contract_required",
        "retention_decision_required",
    ]
    assert result["safe_next_actions"] == [
        "create_audience_contract",
        "record_retention_decision",
    ]
    assert result["next_action"] == "create_audience_contract"


def test_v33_1_blocks_blank_case_identifier():
    result = snapshot.build_case_governance_snapshot(" ")

    assert result["status"] == "blocked"
    assert result["blockers"][0]["key"] == "case_id_required"
    assert result["read_only"] is True
