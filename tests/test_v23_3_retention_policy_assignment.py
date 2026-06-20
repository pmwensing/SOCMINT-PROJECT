from src.socmint import database
from src.socmint import case_retention_assignment_v23_3 as service


def _closed_decision():
    return {
        "closure_decision_id": "closure-decision-1",
        "closure_decision_sha256": "a" * 64,
        "decision_record_id": 82,
        "decision": "close",
        "case_closed": True,
        "decided_by": "supervisor",
        "decided_at": "2026-06-14T21:20:00+00:00",
        "source": {"readiness_review_id": "closure-readiness-1"},
    }


def _setup(tmp_path, monkeypatch, decision=None):
    url = f"sqlite:///{tmp_path / 'app.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    database.configure_database(url)
    monkeypatch.setattr(
        service, "latest_supervisor_closure_decision", lambda case_id: decision
    )
    monkeypatch.setattr(
        service,
        "_retention_policies",
        lambda: [
            {
                "policy_id": "standard_case_retention",
                "display_name": "Standard case retention",
                "retention_years": 7,
                "archive_class": "standard",
                "description": "Seven-year retention.",
            },
            {
                "policy_id": "indefinite_legal_hold",
                "display_name": "Indefinite legal hold",
                "retention_years": None,
                "archive_class": "legal_hold",
                "description": "Hold until released.",
            },
        ],
    )


def test_v23_3_records_catalog_validated_assignment(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, _closed_decision())
    result = service.assign_retention_policy(
        "case-alpha",
        policy_id="standard_case_retention",
        confirmed=True,
        assigner="records-supervisor",
        note="Apply standard disposition.",
    )
    latest = service.latest_retention_assignment("case-alpha")
    assert result["status"] == "retention_assignment_recorded"
    assert result["policy"]["policy_id"] == "standard_case_retention"
    assert result["disposition"]["retention_years"] == 7
    assert result["disposition"]["retention_expires_at"].startswith("2033-06-14")
    assert result["disposition"]["disposition"] == "retain_until_expiration"
    assert result["source"]["closure_decision_id"] == "closure-decision-1"
    assert result["source"]["closure_decision_sha256"] == "a" * 64
    assert result["ready_for_archive_package"] is True
    assert result["source_records_mutated"] is False
    assert result["closure_decision_mutated"] is False
    assert result["archive_package_created"] is False
    assert latest["retention_assignment_id"] == result["retention_assignment_id"]
    assert latest["assigned_by"] == "records-supervisor"


def test_v23_3_requires_close_and_valid_catalog_policy(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, None)
    missing = service.assign_retention_policy(
        "case-alpha",
        policy_id="standard_case_retention",
        confirmed=True,
        assigner="supervisor",
    )
    assert missing["blockers"][0]["key"] == "supervisor_closure_decision_required"

    hold = _closed_decision()
    hold["decision"] = "hold"
    hold["case_closed"] = False
    monkeypatch.setattr(
        service, "latest_supervisor_closure_decision", lambda case_id: hold
    )
    blocked = service.assign_retention_policy(
        "case-alpha",
        policy_id="standard_case_retention",
        confirmed=True,
        assigner="supervisor",
    )
    assert blocked["blockers"][0]["key"] == "closed_supervisor_decision_required"

    monkeypatch.setattr(
        service,
        "latest_supervisor_closure_decision",
        lambda case_id: _closed_decision(),
    )
    invalid = service.assign_retention_policy(
        "case-alpha",
        policy_id="unknown-policy",
        confirmed=True,
        assigner="supervisor",
    )
    assert invalid["blockers"][0]["key"] == "retention_policy_not_in_catalog"

    legal_hold = service.assign_retention_policy(
        "case-alpha",
        policy_id="indefinite_legal_hold",
        confirmed=True,
        assigner="supervisor",
    )
    assert legal_hold["disposition"]["legal_hold"] is True
    assert legal_hold["disposition"]["retention_expires_at"] is None
    assert legal_hold["disposition"]["disposition"] == "hold_until_authorized_release"
