from src.socmint import database
from src.socmint import case_closure_decision_v23_2 as service


def _setup(tmp_path, monkeypatch, review=None):
    url = f"sqlite:///{tmp_path / 'app.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    database.configure_database(url)
    monkeypatch.setattr(
        service, "latest_closure_readiness_review", lambda case_id: review
    )


def _ready_review():
    return {
        "review_id": "closure-readiness-1",
        "review_sha256": "a" * 64,
        "review_record_id": 81,
        "decision": "ready",
        "ready_for_supervisor_closure_decision": True,
        "reviewed_by": "reviewer",
        "reviewed_at": "2026-06-14T21:10:00",
        "source": {"closure_summary": {"case_id": "case-alpha", "closure_ready": True}},
    }


def test_v23_2_records_close_decision_bound_to_ready_review(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, _ready_review())
    result = service.record_supervisor_closure_decision(
        "case-alpha",
        decision="close",
        confirmed=True,
        supervisor="supervisor",
        note="Case lifecycle complete.",
    )
    latest = service.latest_supervisor_closure_decision("case-alpha")
    assert result["status"] == "closure_decision_recorded"
    assert result["decision"] == "close"
    assert result["case_closed"] is True
    assert result["ready_for_retention_assignment"] is True
    assert result["source"]["readiness_review_id"] == "closure-readiness-1"
    assert result["source"]["readiness_review_sha256"] == "a" * 64
    assert result["source_records_mutated"] is False
    assert result["retention_assignment_created"] is False
    assert result["archive_package_created"] is False
    assert result["next_action"] == "assign_retention_policy"
    assert latest["closure_decision_id"] == result["closure_decision_id"]
    assert latest["decided_by"] == "supervisor"


def test_v23_2_blocks_without_ready_review_and_supports_hold_return(
    tmp_path, monkeypatch
):
    _setup(tmp_path, monkeypatch, None)
    missing = service.record_supervisor_closure_decision(
        "case-alpha", decision="close", confirmed=True, supervisor="supervisor"
    )
    assert missing["blockers"][0]["key"] == "closure_readiness_review_required"

    not_ready = _ready_review()
    not_ready["decision"] = "not_ready"
    not_ready["ready_for_supervisor_closure_decision"] = False
    monkeypatch.setattr(
        service, "latest_closure_readiness_review", lambda case_id: not_ready
    )
    blocked = service.record_supervisor_closure_decision(
        "case-alpha", decision="hold", confirmed=True, supervisor="supervisor"
    )
    assert blocked["blockers"][0]["key"] == "ready_closure_readiness_review_required"

    monkeypatch.setattr(
        service, "latest_closure_readiness_review", lambda case_id: _ready_review()
    )
    hold = service.record_supervisor_closure_decision(
        "case-alpha", decision="hold", confirmed=True, supervisor="supervisor"
    )
    returned = service.record_supervisor_closure_decision(
        "case-alpha", decision="return", confirmed=True, supervisor="supervisor"
    )
    assert hold["case_closed"] is False
    assert hold["next_action"] == "review_closure_hold"
    assert returned["case_closed"] is False
    assert returned["next_action"] == "return_case_to_closure_review"
