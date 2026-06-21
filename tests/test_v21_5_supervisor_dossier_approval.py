from src.socmint import database
from src.socmint import dossier_supervisor_approval_v21_5 as service


def _review(ready=True):
    return {
        "status": "ready" if ready else "not_ready",
        "ready": ready,
        "review_id": "review-1",
        "review_sha256": "a" * 64,
        "draft_id": "draft-1",
        "draft_sha256": "b" * 64,
        "mapping_id": "map-1",
        "mapping_sha256": "c" * 64,
        "blockers": [] if ready else [{"key": "citations_unresolved"}],
        "next_action": "request_supervisor_dossier_approval"
        if ready
        else "resolve_dossier_quality_blockers",
    }


def _setup(tmp_path, monkeypatch, ready=True):
    url = f"sqlite:///{tmp_path / 'app.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    database.configure_database(url)
    monkeypatch.setattr(
        service, "build_dossier_quality_review", lambda *a, **k: _review(ready)
    )


def test_v21_5_approve_requires_ready_review(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, ready=False)
    blocked = service.record_supervisor_dossier_decision(
        "case-alpha", "approve", subject_id=42, reviewer="supervisor"
    )
    returned = service.record_supervisor_dossier_decision(
        "case-alpha", "return", subject_id=42, reviewer="supervisor", note="revise"
    )
    held = service.record_supervisor_dossier_decision(
        "case-alpha", "hold", subject_id=42, reviewer="supervisor"
    )
    assert blocked["status"] == "blocked"
    assert blocked["blockers"][0]["key"] == "ready_quality_review_required"
    assert returned["status"] == "returned"
    assert returned["next_action"] == "revise_dossier_assembly"
    assert held["status"] == "held"


def test_v21_5_approval_is_immutable_and_export_ready(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, ready=True)
    result = service.record_supervisor_dossier_decision(
        "case-alpha",
        "approve",
        subject_id=42,
        reviewer="supervisor",
        note="approved for export",
    )
    workspace = service.build_supervisor_approval_workspace("case-alpha", subject_id=42)
    assert result["status"] == "approved"
    assert result["source_review_id"] == "review-1"
    assert result["source_review_sha256"] == "a" * 64
    assert result["export_preparation"]["eligible"] is True
    assert result["next_action"] == "prepare_final_export_package"
    assert result["draft_mutated"] is False
    assert result["quality_review_snapshot_mutated"] is False
    assert (
        workspace["latest_decision"]["approval_record_id"]
        == result["approval_record_id"]
    )
