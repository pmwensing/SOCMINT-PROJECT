from src.socmint import database
from src.socmint import case_reopen_control_v23_5 as service


def _archive():
    return {
        "archive_package_id": "case-archive-1",
        "archive_package_sha256": "archive-hash",
        "archive_record_id": 84,
    }


def _closure():
    return {
        "closure_decision_id": "closure-decision-1",
        "closure_decision_sha256": "closure-hash",
        "decision_record_id": 82,
        "decision": "close",
        "case_closed": True,
    }


def _setup(tmp_path, monkeypatch, archive=True, closure=True):
    url = f"sqlite:///{tmp_path / 'app.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    database.configure_database(url)
    monkeypatch.setattr(
        service,
        "latest_case_archive_package",
        lambda case_id: _archive() if archive else None,
    )
    monkeypatch.setattr(
        service,
        "latest_supervisor_closure_decision",
        lambda case_id: _closure() if closure else None,
    )


def test_v23_5_records_request_bound_to_archive_and_closure(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    result = service.create_reopen_request(
        "case-alpha",
        reason="New material requires further analysis.",
        confirmed=True,
        requester="analyst",
        note="Requesting controlled reopening.",
    )
    latest = service.latest_reopen_request("case-alpha")

    assert result["status"] == "reopen_request_recorded"
    assert result["source"]["archive_package_id"] == "case-archive-1"
    assert result["source"]["archive_package_sha256"] == "archive-hash"
    assert result["source"]["closure_decision_id"] == "closure-decision-1"
    assert result["authorization_required"] is True
    assert result["case_reopened"] is False
    assert result["source_records_mutated"] is False
    assert result["closed_case_mutated"] is False
    assert result["archive_package_mutated"] is False
    assert latest["reopen_request_id"] == result["reopen_request_id"]


def test_v23_5_requires_archive_and_supports_authorize_or_deny(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, archive=False)
    blocked = service.create_reopen_request(
        "case-alpha",
        reason="New evidence.",
        confirmed=True,
        requester="analyst",
    )
    assert blocked["blockers"][0]["key"] == "archive_package_required"

    _setup(tmp_path, monkeypatch)
    request_result = service.create_reopen_request(
        "case-alpha",
        reason="New evidence.",
        confirmed=True,
        requester="analyst",
    )
    assert request_result["status"] == "reopen_request_recorded"

    authorized = service.authorize_reopen_request(
        "case-alpha",
        decision="authorize",
        confirmed=True,
        supervisor="supervisor",
        note="Reopening approved.",
    )
    denied = service.authorize_reopen_request(
        "case-alpha",
        decision="deny",
        confirmed=True,
        supervisor="supervisor",
        note="Further work not justified.",
    )

    assert authorized["status"] == "reopen_authorization_recorded"
    assert authorized["case_reopen_authorized"] is True
    assert authorized["case_reopened"] is True
    assert authorized["next_action"] == "resume_case_operations"
    assert (
        authorized["source"]["reopen_request_id"] == request_result["reopen_request_id"]
    )
    assert authorized["source"]["archive_package_id"] == "case-archive-1"
    assert authorized["source"]["closure_decision_id"] == "closure-decision-1"
    assert authorized["reopen_request_mutated"] is False
    assert authorized["closed_case_mutated_before_authorization"] is False
    assert authorized["archive_package_mutated"] is False

    assert denied["case_reopen_authorized"] is False
    assert denied["case_reopened"] is False
    assert denied["next_action"] == "keep_case_closed"
