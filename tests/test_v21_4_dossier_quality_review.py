from src.socmint import database
from src.socmint import dossier_quality_review_v21_4 as service


def _draft():
    finding = {
        "finding_id": "finding-1",
        "confidence": "high",
        "provenance_sha256": "a" * 64,
        "provenance": {
            "claim_ids": ["assertion:1"],
            "evidence_ids": ["evidence-1"],
            "entity_ids": [],
            "timeline_refs": [],
        },
    }
    return {
        "status": "complete",
        "draft_id": "draft-1",
        "draft_sha256": "b" * 64,
        "sections": [
            {
                "section_id": "key_findings",
                "title": "Key Findings",
                "position": 1,
                "narrative": "Supported narrative.",
                "finding_count": 1,
                "findings": [finding],
                "completeness": {"complete": True, "score": 100.0, "missing": []},
            }
        ],
    }


def _mapping(unresolved=False):
    finding = {
        **_draft()["sections"][0]["findings"][0],
        "resolved_evidence_count": 1,
        "citation_labels": ["C1"],
        "unresolved_claim_ids": ["missing"] if unresolved else [],
        "unresolved_evidence_ids": [],
    }
    unresolved_rows = (
        [
            {
                "key": "unresolved_claim",
                "section_id": "key_findings",
                "finding_id": "finding-1",
                "reference": "missing",
            }
        ]
        if unresolved
        else []
    )
    return {
        "status": "unresolved_citations" if unresolved else "citation_ready",
        "mapping_id": "map-1",
        "mapping_sha256": "c" * 64,
        "unresolved_count": len(unresolved_rows),
        "unresolved": unresolved_rows,
        "sections": [
            {
                "section_id": "key_findings",
                "citations_complete": not unresolved,
                "findings": [finding],
            }
        ],
    }


def test_v21_4_ready_review_is_deterministic(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    database.configure_database(f"sqlite:///{tmp_path / 'app.db'}")
    monkeypatch.setattr(
        service, "build_dossier_section_draft", lambda *a, **k: _draft()
    )
    monkeypatch.setattr(
        service, "build_dossier_citation_mapping", lambda *a, **k: _mapping()
    )
    one = service.build_dossier_quality_review("case-alpha", subject_id=42)
    two = service.build_dossier_quality_review("case-alpha", subject_id=42)
    assert one["status"] == "ready"
    assert one["ready"] is True
    assert one["review_id"] == two["review_id"]
    assert one["review_sha256"] == two["review_sha256"]
    assert one["narrative_coverage_percent"] == 100.0
    assert one["provenance_quality_percent"] == 100.0
    assert one["source_readiness_percent"] == 100.0
    assert one["blocker_count"] == 0


def test_v21_4_explicit_blockers_and_snapshot(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    database.configure_database(f"sqlite:///{tmp_path / 'app.db'}")
    monkeypatch.setattr(
        service, "build_dossier_section_draft", lambda *a, **k: _draft()
    )
    monkeypatch.setattr(
        service, "build_dossier_citation_mapping", lambda *a, **k: _mapping(True)
    )
    review = service.build_dossier_quality_review("case-alpha", subject_id=42)
    saved = service.save_dossier_quality_review_snapshot(
        "case-alpha", subject_id=42, actor="supervisor"
    )
    assert review["status"] == "not_ready"
    assert "citations_unresolved" in review["blocker_keys"]
    assert "unresolved_claim" in review["blocker_keys"]
    assert saved["status"] == "saved"
    assert saved["ready"] is False
    assert saved["source_package_mutated"] is False
    assert saved["arrangement_history_mutated"] is False
    assert saved["draft_snapshot_mutated"] is False
    assert saved["citation_snapshot_mutated"] is False
