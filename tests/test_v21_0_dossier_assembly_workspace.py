from pathlib import Path

from src.socmint import database
from src.socmint.case_findings_v20 import (
    build_dossier_promotion_package,
    decide_finding,
    list_findings,
    propose_finding,
)
from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import (
    register_dossier_assembly_routes_v21_0,
)
from src.socmint.dossier_assembly_workspace_v21_0 import (
    DOSSIER_ARRANGEMENT_ACTION,
    DOSSIER_ASSEMBLY_SCHEMA,
    build_dossier_assembly_workspace,
    save_dossier_arrangement,
)


def _configure(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'app.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    database.configure_database(url)


def _app(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def _promoted(case_id="case-alpha"):
    proposal = propose_finding(
        case_id,
        {
            "text": "The reviewed account belongs to the subject.",
            "confidence": "high",
            "claim_ids": ["claim-1"],
            "evidence_ids": ["evidence-1"],
            "entity_ids": ["entity-1"],
        },
        actor="analyst",
    )
    decide_finding(case_id, proposal["finding_id"], "approve", actor="supervisor")
    package = build_dossier_promotion_package(case_id, actor="supervisor", promote=True)
    return proposal, package


def test_v21_0_loads_promoted_v20_package_without_mutation(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    proposal, package = _promoted()
    before = list_findings("case-alpha")

    workspace = build_dossier_assembly_workspace("case-alpha")
    after = list_findings("case-alpha")

    assert workspace["schema"] == DOSSIER_ASSEMBLY_SCHEMA
    assert workspace["source_package"]["package_id"] == package["package_id"]
    assert workspace["finding_count"] == 1
    assert workspace["source_package_immutable"] is True
    assert workspace["source_findings_immutable"] is True
    assert before == after
    assert (
        workspace["sections"][2]["findings"][0]["finding_id"] == proposal["finding_id"]
    )


def test_v21_0_groups_findings_and_exposes_narrative_gaps(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    _promoted()

    workspace = build_dossier_assembly_workspace("case-alpha")

    identity = next(
        section
        for section in workspace["sections"]
        if section["section_id"] == "identity_and_entities"
    )
    assert identity["finding_count"] == 1
    assert workspace["gap_summary"]["missing_narrative"] == 1
    assert workspace["gap_summary"]["missing_evidence"] == 0
    assert workspace["gap_summary"]["missing_citation"] == 0


def test_v21_0_saves_immutable_arrangement_and_reloads_it(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    proposal, package = _promoted()

    saved = save_dossier_arrangement(
        "case-alpha",
        {
            "section_order": [
                "executive_summary",
                "identity_and_entities",
                "key_findings",
            ],
            "finding_sections": {proposal["finding_id"]: "executive_summary"},
            "narratives": {
                "executive_summary": "The approved finding establishes ownership."
            },
        },
        actor="operator",
    )
    workspace = build_dossier_assembly_workspace("case-alpha")

    assert saved["status"] == "saved"
    assert saved["source_package_id"] == package["package_id"]
    assert saved["source_records_mutated"] is False
    assert len(saved["arrangement_sha256"]) == 64
    assert workspace["sections"][0]["section_id"] == "executive_summary"
    assert workspace["sections"][0]["finding_count"] == 1
    assert workspace["sections"][0]["narrative"].startswith("The approved")
    assert workspace["gap_count"] == 0

    session = database.Session()
    try:
        assert (
            session.query(database.AuditLog)
            .filter_by(
                action=DOSSIER_ARRANGEMENT_ACTION,
                target_value="case-alpha",
            )
            .count()
            == 1
        )
    finally:
        session.close()


def test_v21_0_exposes_existing_product_links(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    _promoted()

    workspace = build_dossier_assembly_workspace("case-alpha", subject_id=42)
    links = workspace["integration_links"]

    assert links["case_findings_workspace"] == "/case-findings/case-alpha"
    assert links["case_delivery_workspace"] == "/case-delivery?case_id=case-alpha"
    assert links["dossier_readiness_api"] == "/api/v1/subjects/42/dossier/readiness"
    assert (
        links["claim_evidence_ledger_api"]
        == "/api/v1/subjects/42/claim-evidence-ledger"
    )
    assert links["export_manifest_draft"] == "/api/v1/subjects/42/export-manifest-draft"
    assert links["ultimate_dossier"] == "/spine/subjects/42/ultimate-dossier"


def test_v21_0_routes_auth_ui_and_arrangement(tmp_path, monkeypatch):
    client = _app(tmp_path, monkeypatch).test_client()
    assert client.get("/api/v1/dossier-assembly/case-alpha").status_code == 401
    assert client.get("/dossier-assembly/case-alpha").status_code == 302

    _promoted()
    with client.session_transaction() as sess:
        sess["user"] = "operator"
        sess["_csrf_token"] = "test-csrf"

    api = client.get("/api/v1/dossier-assembly/case-alpha?subject_id=42")
    ui = client.get("/dossier-assembly/case-alpha?subject_id=42")
    save = client.post(
        "/api/v1/dossier-assembly/case-alpha/arrangement",
        json={
            "section_order": ["key_findings"],
            "narratives": {"key_findings": "Approved findings narrative."},
        },
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert api.status_code == 200
    assert api.get_json()["subject_id"] == 42
    assert ui.status_code == 200
    assert b"Dossier Assembly Workspace" in ui.data
    assert b"Assembly Gaps" in ui.data
    assert b"Connected Product Surfaces" in ui.data
    assert save.status_code == 200
    assert save.get_json()["status"] == "saved"


def test_v21_0_artifacts_release_note_and_no_migration():
    note = Path("release/V21_0_DOSSIER_ASSEMBLY_WORKSPACE.md").read_text(
        encoding="utf-8"
    )
    script = Path("src/socmint/static/dossier_assembly_v21_0.js").read_text(
        encoding="utf-8"
    )
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v21_0*")
    ]

    assert "existing dossier" in note
    assert "export manifest" in note
    assert "claim/evidence ledger" in note
    assert "collectArrangement" in script
    assert "source records" in note
    assert migrations == []
