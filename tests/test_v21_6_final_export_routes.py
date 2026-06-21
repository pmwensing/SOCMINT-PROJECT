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


def test_v21_6_routes_ui_and_note(tmp_path, monkeypatch):
    from src.socmint import dossier_final_export_routes_v21_6 as routes

    payload = {
        "status": "ready",
        "case_id": "case-alpha",
        "subject_id": 42,
        "export_package_id": "dossier-export-1",
        "export_package_sha256": "a" * 64,
        "dossier_content": {"section_count": 1, "sections": []},
        "citation_catalog": [],
        "source_manifest": {},
        "approval_record": {"approval_id": "approval-1"},
        "integrity": {"content_sha256": "b" * 64},
        "latest_export": None,
    }
    monkeypatch.setattr(routes, "build_final_export_package", lambda *a, **k: payload)
    monkeypatch.setattr(
        routes,
        "generate_final_export_package",
        lambda *a, **k: {"status": "generated", "export_record_id": 13},
    )
    client = _app(tmp_path, monkeypatch).test_client()
    with client.session_transaction() as sess:
        sess["user"] = "operator"
        sess["_csrf_token"] = "test-csrf"

    assert (
        client.get(
            "/api/v1/dossier-assembly/case-alpha/final-export?subject_id=42"
        ).status_code
        == 200
    )
    ui = client.get("/dossier-assembly/case-alpha/final-export?subject_id=42")
    assert b"Final Export Package Generation" in ui.data
    assert b"Integrity Manifest" in ui.data
    response = client.post(
        "/api/v1/dossier-assembly/case-alpha/final-export?subject_id=42",
        json={},
        headers={"X-CSRF-Token": "test-csrf"},
    )
    assert response.status_code == 200
    assert response.get_json()["export_record_id"] == 13

    note = Path("release/V21_6_PACKAGE_GENERATION.md").read_text(encoding="utf-8")
    script = Path("src/socmint/static/dossier_final_export_v21_6.js").read_text(
        encoding="utf-8"
    )
    migrations = [
        p
        for d in (Path("migrations"), Path("alembic"))
        if d.exists()
        for p in d.rglob("*v21_6*")
    ]
    assert "returned or held" in note
    assert "citation catalog" in note
    assert "integrity hashes" in note
    assert "final-export" in script
    assert migrations == []
