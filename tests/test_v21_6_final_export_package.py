from src.socmint import database
from src.socmint import dossier_final_export_package_v21_6 as service


def _approval(status="approved"):
    return {
        "result_status": status,
        "approval_id": "approval-1",
        "approval_record_id": 11,
        "decision_sha256": "d" * 64,
        "reviewer": "supervisor",
        "decided_at": "2026-06-14T00:00:00+00:00",
        "note": "approved",
        "source_review_id": "review-1",
        "source_review_sha256": "a" * 64,
        "export_preparation": {"next_action": "prepare_final_export_package"},
    }


def _draft():
    return {
        "status": "complete",
        "draft_id": "draft-1",
        "draft_sha256": "b" * 64,
        "source_package_id": "package-1",
        "source_manifest_sha256": "c" * 64,
        "source_import_record_id": 4,
        "source_arrangement_record_id": 5,
        "source_arrangement_sha256": "e" * 64,
    }


def _citations():
    return {
        "status": "citation_ready",
        "mapping_id": "mapping-1",
        "mapping_sha256": "f" * 64,
        "citation_catalog": [{"label": "C1", "claim_id": "claim-1"}],
        "sections": [
            {
                "section_id": "key_findings",
                "title": "Key Findings",
                "position": 1,
                "citation_ready_narrative": "Narrative [C1]",
                "findings": [{"citation_ready_text": "Finding [C1]"}],
            }
        ],
    }


def _review(review_id="review-1"):
    return {
        "status": "ready",
        "ready": True,
        "review_id": review_id,
        "review_sha256": "a" * 64,
    }


def _setup(tmp_path, monkeypatch, approval=None, review_id="review-1"):
    url = f"sqlite:///{tmp_path / 'app.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    database.configure_database(url)
    monkeypatch.setattr(service, "_latest_decision", lambda case_id: approval)
    monkeypatch.setattr(
        service, "build_dossier_section_draft", lambda *a, **k: _draft()
    )
    monkeypatch.setattr(
        service, "build_dossier_citation_mapping", lambda *a, **k: _citations()
    )
    monkeypatch.setattr(
        service, "build_dossier_quality_review", lambda *a, **k: _review(review_id)
    )


def test_v21_6_refuses_missing_returned_and_held(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, None)
    assert (
        service.build_final_export_package("case-alpha", subject_id=42)["blockers"][0][
            "key"
        ]
        == "supervisor_approval_required"
    )
    for status in ("returned", "held"):
        monkeypatch.setattr(
            service, "_latest_decision", lambda case_id, s=status: _approval(s)
        )
        result = service.build_final_export_package("case-alpha", subject_id=42)
        assert result["status"] == "blocked"
        assert result["blockers"][0]["key"] == f"latest_supervisor_decision_{status}"


def test_v21_6_deterministic_package_and_generation(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, _approval())
    one = service.build_final_export_package("case-alpha", subject_id=42)
    two = service.build_final_export_package("case-alpha", subject_id=42)
    generated = service.generate_final_export_package(
        "case-alpha", subject_id=42, actor="operator"
    )
    assert one["status"] == "ready"
    assert one["export_package_id"] == two["export_package_id"]
    assert one["export_package_sha256"] == two["export_package_sha256"]
    assert one["dossier_content"]["sections"][0]["citation_ready_narrative"].endswith(
        "[C1]"
    )
    assert one["approval_record"]["approval_record_id"] == 11
    assert set(one["integrity"]) == {
        "content_sha256",
        "dossier_sha256",
        "citation_catalog_sha256",
        "source_manifest_sha256",
        "approval_record_sha256",
        "quality_review_sha256",
    }
    assert generated["status"] == "generated"
    assert generated["next_action"] == "handoff_final_export_package"
    assert generated["source_records_mutated"] is False


def test_v21_6_refuses_stale_approval(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, _approval(), review_id="review-new")
    result = service.build_final_export_package("case-alpha", subject_id=42)
    assert result["status"] == "blocked"
    assert result["blockers"][0]["key"] == "supervisor_approval_stale"
    assert result["next_action"] == "request_supervisor_dossier_approval"
