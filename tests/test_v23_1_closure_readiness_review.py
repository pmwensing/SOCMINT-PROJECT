from src.socmint import database
from src.socmint import case_closure_readiness_review_v23_1 as service


def _setup(tmp_path, monkeypatch, eligible=True):
    url = f"sqlite:///{tmp_path / 'app.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    database.configure_database(url)
    monkeypatch.setattr(
        service,
        "build_case_closure_workspace",
        lambda case_id: {
            "version": "v23.0.0",
            "status": "eligible_for_closure_review" if eligible else "blocked",
            "closure_eligible": eligible,
            "archive_ready": eligible,
            "current_release_outcome": "delivered_and_acknowledged"
            if eligible
            else "delivery_failed",
            "blockers": []
            if eligible
            else [{"key": "release_closure_readiness_required"}],
            "release_history": {
                "closure_summary": {
                    "case_id": case_id,
                    "closure_ready": eligible,
                    "acknowledgement_id": "ack-1" if eligible else None,
                }
            },
            "proposed_retention_policy": {"policy_id": "standard_case_retention"},
        },
    )


def test_v23_1_records_ready_review(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, True)
    result = service.review_case_closure_readiness(
        "case-alpha",
        decision="ready",
        confirmed=True,
        reviewer="supervisor",
        note="All closure prerequisites reviewed.",
    )
    latest = service.latest_closure_readiness_review("case-alpha")
    assert result["status"] == "review_recorded"
    assert result["decision"] == "ready"
    assert result["ready_for_supervisor_closure_decision"] is True
    assert result["source"]["closure_eligible"] is True
    assert result["source"]["proposed_retention_policy_id"] == "standard_case_retention"
    assert result["source_records_mutated"] is False
    assert result["closure_record_created"] is False
    assert latest["review_id"] == result["review_id"]
    assert latest["reviewed_by"] == "supervisor"


def test_v23_1_blocks_ready_when_case_not_eligible_and_allows_not_ready(
    tmp_path, monkeypatch
):
    _setup(tmp_path, monkeypatch, False)
    blocked = service.review_case_closure_readiness(
        "case-alpha",
        decision="ready",
        confirmed=True,
        reviewer="supervisor",
    )
    assert blocked["status"] == "blocked"
    assert blocked["blockers"][0]["key"] == "release_closure_readiness_required"

    recorded = service.review_case_closure_readiness(
        "case-alpha",
        decision="not_ready",
        confirmed=True,
        reviewer="supervisor",
        note="Delivery failure remains unresolved.",
    )
    assert recorded["status"] == "review_recorded"
    assert recorded["decision"] == "not_ready"
    assert recorded["ready_for_supervisor_closure_decision"] is False
    assert recorded["next_action"] == "resolve_closure_readiness_blockers"
