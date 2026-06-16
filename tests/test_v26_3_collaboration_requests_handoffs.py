from src.socmint import collaboration_requests_handoffs_v26_3 as service


def test_v26_3_create_request_and_handoff(monkeypatch):
    monkeypatch.setattr(service,"_case_state",lambda case_id:{"case":{"case_id":case_id}})
    monkeypatch.setattr(service,"_record",lambda *args,**kwargs:(10,"2026-06-16T15:00:00+00:00"))
    req=service.create_request("case-a",actor="paul",other="alice",item_type="evidence_review",reason="Review package",priority="high",due_at="2026-06-17",source_records=[{"id":1,"sha256":"a"*64}],confirmed=True,allowed_case_ids={"case-a"},ip_address=None)
    hand=service.create_handoff("case-a",actor="paul",other="bob",item_type="review_task",reason="Take over review",priority="normal",due_at=None,source_records=[],confirmed=True,allowed_case_ids={"case-a"},ip_address=None)
    assert req["status"]=="collaboration_request_recorded"
    assert req["workflow_status"]=="requested"
    assert req["source_records_sha256"]
    assert req["source_records_mutated"] is False
    assert hand["status"]=="collaboration_handoff_recorded"
    assert hand["workflow_status"]=="pending"
    assert hand["prior_events_mutated"] is False


def test_v26_3_transition_binds_source_and_blocks_terminal(monkeypatch):
    item={"collaboration_request_id":"r1","collaboration_request_sha256":"b"*64,"action_record_id":5,"workflow_status":"requested"}
    monkeypatch.setattr(service,"current_items",lambda case_id:{"requests":[item],"handoffs":[]})
    monkeypatch.setattr(service,"_record",lambda *args,**kwargs:(11,"2026-06-16T16:00:00+00:00"))
    result=service.transition("request","case-a","r1",actor="alice",decision="accepted",reason="Will review",confirmed=True,allowed_case_ids={"case-a"})
    assert result["status"]=="collaboration_request_accepted"
    assert result["request_binding"]["action_record_id"]==5
    assert result["source_event_mutated"] is False
    monkeypatch.setattr(service,"current_items",lambda case_id:{"requests":[{**item,"workflow_status":"completed"}],"handoffs":[]})
    blocked=service.transition("request","case-a","r1",actor="alice",decision="accepted",reason="again",confirmed=True,allowed_case_ids={"case-a"})
    assert blocked["blockers"][0]["key"]=="open_collaboration_request_required"


def test_v26_3_access_and_catalog_validation(monkeypatch):
    denied=service.create_request("hidden",actor="paul",other="alice",item_type="evidence_review",reason="x",priority="normal",due_at=None,source_records=[],confirmed=True,allowed_case_ids={"case-a"},ip_address=None)
    invalid=service.create_handoff("case-a",actor="paul",other="alice",item_type="unknown",reason="x",priority="normal",due_at=None,source_records=[],confirmed=True,allowed_case_ids={"case-a"},ip_address=None)
    assert denied["blockers"][0]["key"]=="case_access_required"
    assert invalid["blockers"][0]["key"]=="collaboration_handoff_type_not_in_catalog"
