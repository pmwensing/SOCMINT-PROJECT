
from pathlib import Path
import zipfile

from socmint.dashboard import create_app
from socmint.evidence_integrity import build_custody_export_pack
from socmint.evidence_integrity import integrity_dashboard_payload
from socmint.evidence_integrity import list_custody_export_packs
from socmint.evidence_intake import intake_evidence_file
from socmint.evidence_links import link_evidence_to_review_item


def test_integrity_dashboard_payload(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    source = tmp_path / "integrity.txt"
    source.write_text("integrity")

    evidence = intake_evidence_file(source, case_id="case-integrity")
    link_evidence_to_review_item(evidence["evidence_id"], "findings:11")

    payload = integrity_dashboard_payload(case_id="case-integrity")

    assert payload["schema"] == "socmint.evidence_integrity_dashboard.v7_4_3"
    assert payload["evidence_count"] == 1
    assert payload["link_count"] >= 1
    assert payload["custody_event_count"] >= 2


def test_custody_export_pack_zip(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    source = tmp_path / "pack.pdf"
    source.write_bytes(b"pack evidence")

    evidence = intake_evidence_file(source, case_id="case-pack", subject_id=7)
    link_evidence_to_review_item(evidence["evidence_id"], "findings:pack")

    result = build_custody_export_pack(
        case_id="case-pack",
        subject_id=7,
        actor="tester",
    )

    assert result["schema"] == "socmint.custody_export_pack.v7_4_3"
    assert Path(result["zip_path"]).exists()
    assert Path(result["manifest_path"]).exists()

    with zipfile.ZipFile(result["zip_path"]) as zf:
        names = set(zf.namelist())
        assert "README.txt" in names
        assert any(name.endswith("-MANIFEST.json") for name in names)
        assert any(name.endswith("-DASHBOARD.json") for name in names)
        assert "CHAIN-OF-CUSTODY.json" in names
        assert "EVIDENCE-MANIFEST.json" in names

    packs = list_custody_export_packs()
    assert packs
    assert packs[0]["name"].endswith(".zip")


def test_integrity_routes_registered():
    app = create_app()
    rules = {rule.rule for rule in app.url_map.iter_rules()}

    assert "/evidence/integrity" in rules
    assert "/api/v1/evidence/integrity" in rules
    assert "/api/v1/evidence/integrity/pack" in rules
    assert "/evidence/integrity/pack/run" in rules
    assert "/evidence/integrity/packs/<path:name>/download" in rules
