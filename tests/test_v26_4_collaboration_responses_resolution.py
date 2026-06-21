import datetime as dt

from src.socmint import collaboration_responses_resolution_v26_4 as service


class _FakeSession:
    def __init__(self):
        self.row = None

    def add(self, row):
        self.row = row

    def commit(self):
        self.row.id = 201
        self.row.created_at = dt.datetime(2026, 6, 16, 18, 0, tzinfo=dt.UTC)

    def refresh(self, row):
        return None

    def close(self):
        return None


def _patch_recording(monkeypatch):
    monkeypatch.setattr(service, "_ensure_storage", lambda: None)
    monkeypatch.setattr(service.database, "Session", _FakeSession)
    monkeypatch.setattr(
        service,
        "_case_state",
        lambda case_id: {
            "portfolio_schema": "socmint.portfolio_operations_dashboard.v24_0",
            "portfolio_version": "v24.0.0",
            "case": {"case_id": case_id, "stage": "active", "status": "operational"},
        },
    )
    monkeypatch.setattr(service, "latest_response_state", lambda *args, **kwargs: None)


def test_v26_4_records_response_bound_to_request(monkeypatch):
    _patch_recording(monkeypatch)
    monkeypatch.setattr(
        service,
        "_source_item",
        lambda *args: {
            "collaboration_request_id": "request-1",
            "collaboration_request_sha256": "r" * 64,
            "action_record_id": 55,
            "workflow_status": "requested",
            "requested_by": "paul",
            "requested_from": "alice",
        },
    )

    result = service.record_collaboration_response(
        "case-a",
        target_type="request",
        target_id="request-1",
        response_type="acceptance",
        responding_user="alice",
        reason="I will complete the evidence review.",
        confirmed=True,
        allowed_case_ids={"case-a"},
    )

    assert result["status"] == "collaboration_response_recorded"
    assert result["source_binding"]["target_id"] == "request-1"
    assert result["source_binding"]["target_sha256"] == "r" * 64
    assert result["source_binding"]["current_state"] == "requested"
    assert result["source_case_state_sha256"]
    assert len(result["collaboration_response_sha256"]) == 64
    assert result["source_records_mutated"] is False
    assert result["source_event_mutated"] is False
    assert result["prior_response_mutated"] is False
    assert result["case_access_scope_changed"] is False


def test_v26_4_escalation_then_resolution_binds_previous_response(monkeypatch):
    _patch_recording(monkeypatch)
    monkeypatch.setattr(
        service,
        "_source_item",
        lambda *args: {
            "collaboration_handoff_id": "handoff-1",
            "collaboration_handoff_sha256": "h" * 64,
            "action_record_id": 60,
            "workflow_status": "accepted",
            "handoff_from": "paul",
            "handoff_to": "bob",
        },
    )
    previous = {
        "collaboration_response_id": "response-1",
        "collaboration_response_sha256": "p" * 64,
        "response_type": "escalation",
        "action_record_id": 70,
    }
    monkeypatch.setattr(
        service, "latest_response_state", lambda *args, **kwargs: previous
    )

    result = service.record_collaboration_response(
        "case-a",
        target_type="handoff",
        target_id="handoff-1",
        response_type="resolution",
        responding_user="supervisor",
        reason="Ownership handoff resolved.",
        resolution_code="resolved_reassignment",
        confirmed=True,
        allowed_case_ids={"case-a"},
    )

    assert result["response_type"] == "resolution"
    assert (
        result["previous_response_binding"]["collaboration_response_id"] == "response-1"
    )
    assert result["previous_response_binding_sha256"]
    assert result["resolution_code"] == "resolved_reassignment"


def test_v26_4_blocks_invalid_access_superseded_note_and_terminal_response(monkeypatch):
    denied = service.record_collaboration_response(
        "hidden",
        target_type="request",
        target_id="request-1",
        response_type="acknowledgement",
        responding_user="alice",
        reason="Seen.",
        confirmed=True,
        allowed_case_ids={"case-a"},
    )
    assert denied["blockers"][0]["key"] == "case_access_required"

    monkeypatch.setattr(
        service,
        "_source_item",
        lambda *args: {
            "collaboration_note_id": "note-1",
            "collaboration_note_sha256": "n" * 64,
            "note_status": "superseded",
        },
    )
    superseded = service.record_collaboration_response(
        "case-a",
        target_type="note",
        target_id="note-1",
        response_type="acknowledgement",
        responding_user="alice",
        reason="Seen.",
        confirmed=True,
        allowed_case_ids={"case-a"},
    )
    assert superseded["blockers"][0]["key"] == "active_collaboration_note_required"

    monkeypatch.setattr(
        service,
        "_source_item",
        lambda *args: {
            "collaboration_request_id": "request-1",
            "collaboration_request_sha256": "r" * 64,
            "workflow_status": "accepted",
        },
    )
    monkeypatch.setattr(
        service,
        "latest_response_state",
        lambda *args, **kwargs: {"response_type": "resolution"},
    )
    terminal = service.record_collaboration_response(
        "case-a",
        target_type="request",
        target_id="request-1",
        response_type="response_note",
        responding_user="alice",
        reason="Another note.",
        confirmed=True,
        allowed_case_ids={"case-a"},
    )
    assert terminal["blockers"][0]["key"] == "open_collaboration_response_required"
