from pathlib import Path

from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import (
    register_dossier_assembly_routes_v21_0,
)


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def _payload():
    return {
        "schema": "socmint.dossier_quality_review.v21_4",
        "version": "v21.4.0",
        "case_id": "case-alpha",
        "subject_id": 42,
        "status": "ready",
        "ready": True,
        "review_id": "review-1",
        "review_sha256": "a" * 64,
        "draft_id": "draft-1",
        "draft_sha256": "b" * 64,
        "mapping_id": "map-1",
        "mapping_sha256": "c" * 64,
        "section_count": 1,
        "ready_section_count": 1,
        "narrative_coverage_percent": 100.0,
        "provenance_quality_percent": 100.0,
        "source_readiness_percent": 100.0,
        "unresolved_citation_count": 0,
        "section_reviews": [
            {
                "section_id": "key_findings",
                "title": "Key Findings",
                "position": 1,
                "finding_count": 1,
                "narrative_covered": True,
                "section_completeness": {"score": 100.0},
                "citations_complete": True,
                "ready": True,
                "finding_reviews": [
                    {
                        "finding_id": "finding-1",
                        "provenance_quality": {"score": 100.0, "missing": []},
                        "source_ready": True,
                        "citation_labels": ["C1"],
                    }
                ],
            }
        ],
        "blocker_count": 0,
        "blocker_keys": [],
        "blockers": [],
        "latest_snapshot": None,
    }


def test_v21_4_routes_and_ui(tmp_path, monkeypatch):
    from src.socmint import dossier_quality_review_routes_v21_4 as routes

    monkeypatch.setattr(
        routes, "build_dossier_quality_review", lambda *a, **k: _payload()
    )
    monkeypatch.setattr(
        routes,
        "save_dossier_quality_review_snapshot",
        lambda *a, **k: {"status": "saved", "snapshot_record_id": 9},
    )
    client = _app(tmp_path, monkeypatch).test_client()
    with client.session_transaction() as sess:
        sess["user"] = "supervisor"
        sess["_csrf_token"] = "test-csrf"
    api = client.get("/api/v1/dossier-assembly/case-alpha/quality-review?subject_id=42")
    ui = client.get("/dossier-assembly/case-alpha/quality-review?subject_id=42")
    saved = client.post(
        "/api/v1/dossier-assembly/case-alpha/quality-review-snapshot?subject_id=42",
        json={},
        headers={"X-CSRF-Token": "test-csrf"},
    )
    assert api.status_code == 200
    assert ui.status_code == 200
    assert b"Dossier Quality and Completeness Review" in ui.data
    assert b"Explicit Blockers" in ui.data
    assert b"Provenance quality" in ui.data
    assert saved.status_code == 200
    assert saved.get_json()["snapshot_record_id"] == 9


def test_v21_4_release_note_client_and_no_migration():
    note = Path("release/V21_4_DOSSIER_QUALITY_COMPLETENESS_REVIEW.md").read_text(
        encoding="utf-8"
    )
    script = Path("src/socmint/static/dossier_quality_review_v21_4.js").read_text(
        encoding="utf-8"
    )
    migrations = [
        p
        for d in (Path("migrations"), Path("alembic"))
        if d.exists()
        for p in d.rglob("*v21_4*")
    ]
    assert "section completeness" in note
    assert "unresolved citations" in note
    assert "provenance quality" in note
    assert "source readiness" in note
    assert "quality-review-snapshot" in script
    assert migrations == []
