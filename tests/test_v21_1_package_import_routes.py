from pathlib import Path

from src.socmint import database
from src.socmint.case_findings_v20 import build_dossier_promotion_package, decide_finding, propose_finding
from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import register_dossier_assembly_routes_v21_0


def _app(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'app.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    database.configure_database(url)
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def _promote():
    item = propose_finding("case-alpha", {
        "text": "Approved finding",
        "claim_ids": ["claim-1"],
        "evidence_ids": ["evidence-1"],
    }, actor="analyst")
    decide_finding("case-alpha", item["finding_id"], "approve", actor="supervisor")
    build_dossier_promotion_package("case-alpha", actor="supervisor", promote=True)


def test_v21_1_routes_and_ui(tmp_path, monkeypatch):
    client = _app(tmp_path, monkeypatch).test_client()
    _promote()
    with client.session_transaction() as sess:
        sess["user"] = "operator"
        sess["_csrf_token"] = "test-csrf"
    before = client.get("/api/v1/dossier-assembly/case-alpha/package-import")
    ui = client.get("/dossier-assembly/case-alpha")
    imported = client.post(
        "/api/v1/dossier-assembly/case-alpha/package-import",
        json={}, headers={"X-CSRF-Token": "test-csrf"},
    )
    duplicate = client.post(
        "/api/v1/dossier-assembly/case-alpha/package-import",
        json={}, headers={"X-CSRF-Token": "test-csrf"},
    )
    after = client.get("/api/v1/dossier-assembly/case-alpha")
    assert before.get_json()["status"] == "available_not_imported"
    assert b"Approved Findings Package Import" in ui.data
    assert b"Manifest verification" in ui.data
    assert imported.get_json()["status"] == "imported"
    assert duplicate.get_json()["status"] == "duplicate"
    assert after.get_json()["can_arrange"] is True


def test_v21_1_note_client_and_no_migration():
    note = Path("release/V21_1_IMPORT_APPROVED_FINDINGS_PACKAGE.md").read_text(encoding="utf-8")
    script = Path("src/socmint/static/dossier_assembly_v21_0.js").read_text(encoding="utf-8")
    migrations = [p for d in (Path("migrations"), Path("alembic")) if d.exists() for p in d.rglob("*v21_1*")]
    assert "manifest verification" in note
    assert "duplicate-import protection" in note
    assert "package freshness" in note
    assert "import-findings-package" in script
    assert migrations == []
