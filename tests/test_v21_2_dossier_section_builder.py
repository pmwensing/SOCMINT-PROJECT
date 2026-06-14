from src.socmint import database
from src.socmint.case_findings_v20 import build_dossier_promotion_package, decide_finding, propose_finding
from src.socmint.dossier_assembly_workspace_v21_0 import save_dossier_arrangement
from src.socmint.dossier_package_import_v21_1 import import_dossier_package
from src.socmint.dossier_section_builder_v21_2 import (
    DOSSIER_DRAFT_SNAPSHOT_ACTION,
    build_dossier_section_draft,
    save_dossier_draft_snapshot,
)


def _setup(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'app.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    database.configure_database(url)


def _finding(suffix):
    item = propose_finding("case-alpha", {
        "text": f"Finding {suffix}",
        "claim_ids": [f"claim-{suffix}"],
        "evidence_ids": [f"evidence-{suffix}"],
        "confidence": "high",
    }, actor="analyst")
    decide_finding("case-alpha", item["finding_id"], "approve", actor="supervisor")
    return item["finding_id"]


def _ready_case():
    first = _finding("one")
    second = _finding("two")
    build_dossier_promotion_package("case-alpha", actor="supervisor", promote=True)
    import_dossier_package("case-alpha", actor="operator")
    save_dossier_arrangement("case-alpha", {
        "section_order": ["executive_summary", "key_findings"],
        "finding_sections": {first: "key_findings", second: "key_findings"},
        "narratives": {"key_findings": "Supported findings narrative."},
    }, actor="operator")
    return first, second


def test_v21_2_requires_saved_arrangement(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    _finding("one")
    build_dossier_promotion_package("case-alpha", actor="supervisor", promote=True)
    import_dossier_package("case-alpha", actor="operator")
    result = build_dossier_section_draft("case-alpha")
    assert result["status"] == "blocked"
    assert result["blockers"][0]["key"] == "saved_arrangement_required"


def test_v21_2_deterministic_order_and_completeness(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    first, second = _ready_case()
    order = {"key_findings": [second, first]}
    one = build_dossier_section_draft("case-alpha", finding_order=order)
    two = build_dossier_section_draft("case-alpha", finding_order=order)
    section = next(item for item in one["sections"] if item["section_id"] == "key_findings")
    assert one["draft_id"] == two["draft_id"]
    assert one["draft_sha256"] == two["draft_sha256"]
    assert section["finding_order"] == [second, first]
    assert section["completeness"]["complete"] is True
    assert one["status"] == "complete"
    assert one["completeness_percent"] == 100.0
    assert one["source_records_mutated"] is False


def test_v21_2_snapshot_preserves_sources(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    first, second = _ready_case()
    before = build_dossier_section_draft("case-alpha")
    saved = save_dossier_draft_snapshot(
        "case-alpha",
        actor="operator",
        finding_order={"key_findings": [first, second]},
    )
    after = build_dossier_section_draft("case-alpha")
    assert saved["status"] == "saved"
    assert saved["source_records_mutated"] is False
    assert saved["source_package_id"] == before["source_package_id"]
    assert saved["source_arrangement_record_id"] == before["source_arrangement_record_id"]
    assert after["latest_snapshot"]["snapshot_record_id"] == saved["snapshot_record_id"]
    session = database.Session()
    try:
        assert session.query(database.AuditLog).filter_by(
            action=DOSSIER_DRAFT_SNAPSHOT_ACTION,
            target_value="case-alpha",
        ).count() == 1
    finally:
        session.close()
