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
        "schema": "socmint.dossier_final_export_package.v21_6",
        "version": "v21.6.0",
        "case_id": "case-alpha",
        "subject_id": 42,
        "status": "ready",
        "export_package_id": "dossier-export-1",
        "export_package_sha256": "a" * 64,
        "dossier_content": {
            "section_count": 1,
            "sections": [{
                "position": 1,
                "title": "Key Findings",
                "citation_ready_narrative": "Narrative [C1]",
                "findings": [{"citation_ready_text": "Finding [C1]"}],
            }],
        },
        "citation_catalog": [{
            "label": "C1", "claim_id": "claim-1",
            "claim_value": "value", "source": "ledger",
            "evidence_refs": ["evidence-1"],
        }],
        "source_manifest": {"package_id": "package-1"},
        "approval_record": {
            "approval_id": "approval-1",
            "approval_record_id": 11,
            "reviewer": "supervisor",
        },
        "integrity": {"content_sha256": "b" * 64},
        "latest_export": None,
    }


def test_v21_6_routes_and_ui(tmp_path, monkeypatch):
    from src.socmint import dossier_final_export_routes_v21_6 as routes
    monkeypatch.setattr(routes, "build_final_export_package", lambda *a, **k: _payload())
    monkeypatch.setattr(routes, "generate_final_export_package", lambda *a, **k: {
        "status": "generated", "export_record_id": 13,
        "next_action": "handoff_final_export_package"
    })
    client = _app(tmp_path, monkeypatch).test_client()
    with client.session_transaction() as sess:
        sess["user"] = "operator"
        sess["_csrf_token"] = "test-csrf"
    api = client.get("/api/v1/dossier-assembly/case-alpha/final-export?subject_id=42")
    ui = client.get("/dossier-assembly/case-alpha/final-export?subject_id=42")
    generated = client.post(
        "/api/v1/dossier-assembly/case-alpha/final-export?subject_id=42",
        json={}, headers={"X-CSRF-Token": "test-csrf"},
    )
    assert api.status_code == 200
    assert ui.status_code == 200
    assert b"Final Export Package Generation" in ui.data
    assert b"Integrity Manifest" in ui.data
    assert b"Generate final export package" in ui.data
    assert generated.status_code == 200
    assert generated.get_json()["export_record_id"] == 13


def test_v21_6_release_note_client_and_no_migration():
    note = Path("release/V21_6_FINAL_EXPORT_PACKAGE_GENERATION.md").read_text(encoding="utf-8")
    script = Path("src/socmint/static/dossier_final_export_v21_6.js").read_text(encoding="utf-8")
    migrations = [p for d in (Path("migrations"), Path("alembic")) if d.exists() for p in d.rglob("*v21_6*")]
    assert "returned or held" in note
    assert "citation catalog" in note
    assert "integrity hashes" in note
    assert "final-export" in script
    assert migrations == []
