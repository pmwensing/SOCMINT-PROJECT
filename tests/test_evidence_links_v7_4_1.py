
from pathlib import Path
import zipfile

from socmint.dashboard import create_app
from socmint.evidence_intake import build_attachment_zip
from socmint.evidence_intake import intake_evidence_file
from socmint.evidence_links import evidence_links_payload
from socmint.evidence_links import link_evidence_to_review_item
from socmint.evidence_links import review_item_attachment_map
from socmint.evidence_links import unlink_evidence_from_review_item
from socmint.report_export_center import build_review_gated_manifest


def test_evidence_link_payload(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    source = tmp_path / "support.pdf"
    source.write_bytes(b"fake-pdf")

    evidence = intake_evidence_file(source, case_id="case-link")
    link = link_evidence_to_review_item(
        evidence_id=evidence["evidence_id"],
        review_item_id="findings:123",
        relation="supports",
        confidence=0.91,
        note="supports finding",
    )

    assert link["review_item_id"] == "findings:123"
    assert link["relation"] == "supports"

    payload = evidence_links_payload(review_item_id="findings:123")
    assert payload["schema"] == "socmint.evidence_links_payload.v7_4_1"
    assert payload["count"] == 1
    assert payload["links"][0]["evidence"]["sha256"] == evidence["sha256"]


def test_unlink_evidence(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    source = tmp_path / "unlink.txt"
    source.write_text("unlink me")

    evidence = intake_evidence_file(source)
    link_evidence_to_review_item(evidence["evidence_id"], "findings:77")

    result = unlink_evidence_from_review_item(
        evidence_id=evidence["evidence_id"],
        review_item_id="findings:77",
    )

    assert result["removed"] == 1
    assert evidence_links_payload()["count"] == 0


def test_review_item_attachment_map_and_zip(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    source = tmp_path / "linked-photo.jpg"
    source.write_bytes(b"linked image")

    evidence = intake_evidence_file(source, case_id="case-map")

    export_manifest = build_review_gated_manifest(
        subject_id=None,
        gate_mode="exclude_rejected",
    )

    # The generated test export may have no real review items, so link to one
    # manually and then inject it into the manifest for this unit test.
    manifest_path = Path(export_manifest["manifest_path"])
    data = manifest_path.read_text()
    import json

    payload = json.loads(data)
    payload["included_items"] = [
        {
            "id": "findings:999",
            "status": "approved",
            "quality": "high",
            "source": "unit-test",
            "label": "test",
            "value": "linked evidence item",
        }
    ]
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True))

    link_evidence_to_review_item(
        evidence_id=evidence["evidence_id"],
        review_item_id="findings:999",
        relation="supports",
    )

    mapping = review_item_attachment_map(manifest_path.name)

    assert mapping["review_item_count"] == 1
    assert mapping["attachment_count"] == 1

    result = build_attachment_zip(
        export_manifest_name=manifest_path.name,
        case_id="other-case",
        subject_id=9999,
    )

    assert result["attachment_count"] == 1

    with zipfile.ZipFile(result["zip_path"]) as zf:
        names = set(zf.namelist())
        assert any(name.startswith("evidence/") for name in names)


def test_evidence_link_routes_registered():
    app = create_app()
    rules = {rule.rule for rule in app.url_map.iter_rules()}

    assert "/evidence/links" in rules
    assert "/api/v1/evidence/links" in rules
    assert "/api/v1/evidence/links/delete" in rules
    assert "/evidence/links/add" in rules
    assert "/api/v1/evidence/attachment-map" in rules
