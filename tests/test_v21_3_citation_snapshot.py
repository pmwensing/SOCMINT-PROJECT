from src.socmint import database
from src.socmint.case_findings_v20 import build_dossier_promotion_package, decide_finding, propose_finding
from src.socmint.dossier_assembly_workspace_v21_0 import save_dossier_arrangement
from src.socmint.dossier_citation_mapping_v21_3 import CITATION_SNAPSHOT_ACTION, save_citation_mapping_snapshot
from src.socmint.dossier_package_import_v21_1 import import_dossier_package


def test_v21_3_snapshot_is_immutable(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'app.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    database.configure_database(url)
    item = propose_finding("case-alpha", {
        "text": "Supported finding", "claim_ids": ["assertion:1"],
        "evidence_ids": ["evidence-1"],
    }, actor="analyst")
    decide_finding("case-alpha", item["finding_id"], "approve", actor="supervisor")
    build_dossier_promotion_package("case-alpha", actor="supervisor", promote=True)
    import_dossier_package("case-alpha", actor="operator")
    save_dossier_arrangement("case-alpha", {
        "section_order": ["key_findings"],
        "finding_sections": {item["finding_id"]: "key_findings"},
        "narratives": {"key_findings": "Supported narrative."},
    }, actor="operator")
    from src.socmint import dossier_citation_mapping_v21_3 as service
    monkeypatch.setattr(service, "build_claim_evidence_ledger", lambda subject_id: {
        "schema": "socmint.claim_evidence_ledger.v13_5", "subject_exists": True,
        "rows": [{"claim_id": "assertion:1", "claim_type": "ownership",
            "claim_value": "value", "source": "assertion", "confidence": 1.0,
            "review_state": "confirmed", "evidence_refs": ["evidence-1"],
            "artifact_links": []}],
    })
    result = save_citation_mapping_snapshot(
        "case-alpha", subject_id=42, actor="operator"
    )
    assert result["status"] == "saved"
    assert result["source_package_mutated"] is False
    assert result["draft_snapshot_mutated"] is False
    session = database.Session()
    try:
        assert session.query(database.AuditLog).filter_by(
            action=CITATION_SNAPSHOT_ACTION, target_value="case-alpha"
        ).count() == 1
    finally:
        session.close()
