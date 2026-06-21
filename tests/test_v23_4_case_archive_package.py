from src.socmint import database
from src.socmint import case_archive_package_v23_4 as service


def _setup(tmp_path, monkeypatch, include_assignment=True):
    url = f"sqlite:///{tmp_path / 'app.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    database.configure_database(url)
    assignment = {
        "retention_assignment_id": "retention-assignment-1",
        "retention_assignment_sha256": "assignment-hash",
        "assignment_record_id": 83,
        "ready_for_archive_package": True,
        "policy": {"policy_id": "standard_case_retention"},
        "disposition": {
            "archive_class": "standard",
            "disposition": "retain_until_expiration",
            "retention_expires_at": "2033-06-14T21:20:00+00:00",
            "legal_hold": False,
        },
    }
    monkeypatch.setattr(
        service,
        "latest_retention_assignment",
        lambda case_id: assignment if include_assignment else None,
    )
    monkeypatch.setattr(
        service,
        "latest_supervisor_closure_decision",
        lambda case_id: {
            "closure_decision_id": "closure-decision-1",
            "closure_decision_sha256": "decision-hash",
            "decision": "close",
            "case_closed": True,
        },
    )
    monkeypatch.setattr(
        service,
        "latest_closure_readiness_review",
        lambda case_id: {
            "review_id": "closure-readiness-1",
            "review_sha256": "review-hash",
            "decision": "ready",
        },
    )
    monkeypatch.setattr(
        service,
        "_latest_export",
        lambda case_id: {
            "export_package_id": "dossier-export-1",
            "export_package_sha256": "export-hash",
            "dossier_content": {"sections": [{"section_id": "summary"}]},
        },
    )
    monkeypatch.setattr(
        service,
        "build_release_delivery_history",
        lambda case_id: {
            "closure_ready": True,
            "closure_summary": {
                "case_id": case_id,
                "release_outcome": "delivered_and_acknowledged",
                "acknowledgement_id": "ack-1",
            },
            "timeline": [{"event_id": 1, "event_type": "dispatch"}],
        },
    )


def test_v23_4_requires_retention_assignment(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, include_assignment=False)
    result = service.build_case_archive_package("case-alpha")
    assert result["status"] == "blocked"
    assert result["blockers"][0]["key"] == "retention_assignment_required"


def test_v23_4_builds_and_records_deterministic_archive(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    first = service.build_case_archive_package("case-alpha")
    second = service.build_case_archive_package("case-alpha")
    generated = service.generate_case_archive_package(
        "case-alpha", actor="archive-supervisor"
    )
    latest = service.latest_case_archive_package("case-alpha")

    assert first["status"] == "ready"
    assert first["archive_package_id"] == second["archive_package_id"]
    assert first["archive_package_sha256"] == second["archive_package_sha256"]
    assert first["components"]["closure"]["supervisor_decision"]["decision"] == "close"
    assert (
        first["components"]["retention"]["retention_assignment_id"]
        == "retention-assignment-1"
    )
    assert first["components"]["dossier"]["export_package_id"] == "dossier-export-1"
    assert generated["status"] == "archive_package_generated"
    assert generated["source_records_mutated"] is False
    assert generated["closure_records_mutated"] is False
    assert generated["retention_assignment_mutated"] is False
    assert generated["dossier_records_mutated"] is False
    assert generated["release_delivery_records_mutated"] is False
    assert latest["archive_package_id"] == generated["archive_package_id"]
