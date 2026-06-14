from pathlib import Path

from src.socmint import database
from src.socmint.case_findings_v20 import build_dossier_promotion_package, decide_finding, propose_finding
from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import register_dossier_assembly_routes_v21_0
from src.socmint.dossier_assembly_workspace_v21_0 import save_dossier_arrangement
from src.socmint.dossier_package_import_v21_1 import import_dossier_package


def _app(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'app.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    database.configure_database(url)
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def _ready_case():
    item = propose_finding("case-alpha", {
        "text": "Approved finding",
        "claim_ids": ["claim-1"],
        "evidence_ids": ["evidence-1"],
    }, actor="analyst")
    decide_finding("case-alpha", item["finding_id"], "approve", actor="supervisor")
    build_dossier_promotion_package("case-alpha", actor="supervisor", promote=True)
    import_dossier_package("case-alpha", actor="operator")
    save_dossier_arrangement("case-alpha", {
        "section_order": ["key_findings"],
        "finding_sections": {item["finding_id"]: "key_findings"},
        "narratives": {"key_findings": "Complete narrative."},
    }, actor="operator")


def test_v21_2_routes_and_ui(tmp_path, monkeypatch):
    client = _app(tmp_path, monkeypatch).test_client()
    _ready_case()
    with client.session_transaction() as sess:
        sess["user"] = "operator"
        sess["_csrf_token"] = "test-csrf"
    draft = client.get("/api/v1/dossier-assembly/case-alpha/draft")
    ui = client.get("/dossier-assembly/case-alpha")
    snapshot = client.post(
        "/api/v1/dossier-assembly/case-alpha/draft-snapshot",
        json={}, headers={"X-CSRF-Token": "test-csrf"},
    )
    assert draft.status_code == 200
    assert draft.get_json()["status"] == "complete"
    assert ui.status_code == 200
    assert b"Dossier Section Draft" in ui.data
    assert b"Save draft snapshot" in ui.data
    assert b"Completeness" in ui.data
    assert snapshot.status_code == 200
    assert snapshot.get_json()["status"] == "saved"


def test_v21_2_note_client_and_no_migration():
    note = Path("release/V21_2_DOSSIER_SECTION_BUILDER.md").read_text(encoding="utf-8")
    script = Path("src/socmint/static/dossier_assembly_v21_0.js").read_text(encoding="utf-8")
    migrations = [p for d in (Path("migrations"), Path("alembic")) if d.exists() for p in d.rglob("*v21_2*")]
    assert "section-level completeness" in note
    assert "deterministic draft output" in note
    assert "arrangement history" in note
    assert "collectFindingOrder" in script
    assert "draft-snapshot" in script
    assert migrations == []
