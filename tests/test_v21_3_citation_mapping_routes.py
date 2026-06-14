from pathlib import Path

from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import register_dossier_assembly_routes_v21_0


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def _payload():
    return {
        "schema": "socmint.dossier_citation_mapping.v21_3",
        "version": "v21.3.0",
        "case_id": "case-alpha",
        "subject_id": 42,
        "status": "citation_ready",
        "mapping_id": "citation-map-1",
        "mapping_sha256": "a" * 64,
        "draft_id": "draft-1",
        "draft_sha256": "b" * 64,
        "citation_count": 1,
        "unresolved_count": 0,
        "unresolved": [],
        "citation_catalog": [{
            "label": "C1", "claim_id": "assertion:1",
            "claim_value": "value", "source": "assertion",
            "evidence_refs": ["evidence-1"], "artifact_links": [],
        }],
        "sections": [{
            "section_id": "key_findings", "title": "Key Findings",
            "position": 1, "citation_ready_narrative": "Narrative [C1]",
            "citations_complete": True,
            "findings": [{
                "citation_ready_text": "Finding [C1]",
                "citation_labels": ["C1"],
                "unresolved_claim_ids": [],
                "unresolved_evidence_ids": [],
            }],
        }],
        "latest_snapshot": None,
    }


def test_v21_3_routes_and_ui(tmp_path, monkeypatch):
    from src.socmint import dossier_citation_mapping_routes_v21_3 as routes
    monkeypatch.setattr(routes, "build_dossier_citation_mapping", lambda *a, **k: _payload())
    monkeypatch.setattr(routes, "save_citation_mapping_snapshot", lambda *a, **k: {
        "status": "saved", "snapshot_record_id": 7
    })
    client = _app(tmp_path, monkeypatch).test_client()
    with client.session_transaction() as sess:
        sess["user"] = "operator"
        sess["_csrf_token"] = "test-csrf"
    api = client.get("/api/v1/dossier-assembly/case-alpha/citations?subject_id=42")
    ui = client.get("/dossier-assembly/case-alpha/citations?subject_id=42")
    saved = client.post(
        "/api/v1/dossier-assembly/case-alpha/citation-snapshot?subject_id=42",
        json={}, headers={"X-CSRF-Token": "test-csrf"},
    )
    assert api.status_code == 200
    assert ui.status_code == 200
    assert b"Source and Evidence Citation Mapping" in ui.data
    assert b"Citation-Ready Dossier Content" in ui.data
    assert b"Citation Catalog" in ui.data
    assert saved.status_code == 200
    assert saved.get_json()["snapshot_record_id"] == 7


def test_v21_3_release_note_client_and_no_migration():
    note = Path("release/V21_3_SOURCE_EVIDENCE_CITATION_MAPPING.md").read_text(encoding="utf-8")
    script = Path("src/socmint/static/dossier_citation_mapping_v21_3.js").read_text(encoding="utf-8")
    migrations = [p for d in (Path("migrations"), Path("alembic")) if d.exists() for p in d.rglob("*v21_3*")]
    assert "unresolved citations" in note
    assert "citation-ready dossier content" in note
    assert "draft snapshot" in note
    assert "citation-snapshot" in script
    assert migrations == []
