from src.socmint import database
from src.socmint.case_findings_v20 import build_dossier_promotion_package, decide_finding, propose_finding
from src.socmint.dossier_assembly_workspace_v21_0 import save_dossier_arrangement
from src.socmint.dossier_citation_mapping_v21_3 import build_dossier_citation_mapping
from src.socmint.dossier_package_import_v21_1 import import_dossier_package


def _setup(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'app.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    database.configure_database(url)


def _ready():
    item = propose_finding("case-alpha", {
        "text": "The account belongs to the subject.",
        "claim_ids": ["assertion:1"],
        "evidence_ids": ["evidence-1"],
    }, actor="analyst")
    decide_finding("case-alpha", item["finding_id"], "approve", actor="supervisor")
    build_dossier_promotion_package("case-alpha", actor="supervisor", promote=True)
    import_dossier_package("case-alpha", actor="operator")
    save_dossier_arrangement("case-alpha", {
        "section_order": ["key_findings"],
        "finding_sections": {item["finding_id"]: "key_findings"},
        "narratives": {"key_findings": "The evidence supports attribution."},
    }, actor="operator")


def _ledger(claim_id="assertion:1", refs=None):
    return {
        "schema": "socmint.claim_evidence_ledger.v13_5",
        "subject_id": 42,
        "subject_exists": True,
        "rows": [{
            "claim_id": claim_id,
            "claim_type": "ownership",
            "claim_value": "subject controls account",
            "confidence": 0.95,
            "review_state": "confirmed",
            "source": "spine_dossier_assertion",
            "evidence_refs": ["evidence-1"] if refs is None else refs,
            "artifact_links": [],
        }],
    }


def test_v21_3_citation_ready_output_is_deterministic(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    _ready()
    one = build_dossier_citation_mapping("case-alpha", subject_id=42, ledger_payload=_ledger())
    two = build_dossier_citation_mapping("case-alpha", subject_id=42, ledger_payload=_ledger())
    finding = one["sections"][0]["findings"][0]
    assert one["status"] == "citation_ready"
    assert one["mapping_id"] == two["mapping_id"]
    assert one["mapping_sha256"] == two["mapping_sha256"]
    assert finding["citation_labels"] == ["C1"]
    assert finding["citation_ready_text"].endswith("[C1]")
    assert one["sections"][0]["citation_ready_narrative"].endswith("[C1]")
    assert one["source_package_mutated"] is False
    assert one["draft_snapshot_mutated"] is False


def test_v21_3_unresolved_claim_and_evidence_queue(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    _ready()
    result = build_dossier_citation_mapping(
        "case-alpha", subject_id=42,
        ledger_payload=_ledger("assertion:other", []),
    )
    assert result["status"] == "unresolved_citations"
    assert {item["key"] for item in result["unresolved"]} == {
        "unresolved_claim", "unresolved_evidence"
    }
