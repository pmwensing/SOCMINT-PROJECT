from pathlib import Path
import zipfile

from socmint.dashboard import create_app
from socmint.evidence_intake import (
    build_attachment_zip,
    evidence_intake_payload,
    intake_evidence_file,
    list_evidence,
    safe_evidence_path,
)
from socmint.report_export_center import build_review_gated_manifest


def test_evidence_intake_stores_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    source = tmp_path / "sample.txt"
    source.write_text("hello evidence")

    result = intake_evidence_file(
        source,
        case_id="case-1",
        subject_id=123,
        source_note="unit test",
    )

    assert result["case_id"] == "case-1"
    assert result["subject_id"] == 123
    assert result["sha256"]
    assert Path(result["path"]).exists()

    items = list_evidence(case_id="case-1", subject_id=123)
    assert len(items) == 1

    safe = safe_evidence_path(result["stored_name"])
    assert safe.exists()


def test_evidence_payload_shape(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    payload = evidence_intake_payload()

    assert payload["schema"] == "socmint.evidence_intake.v7_4"
    assert payload["items"] == []


def test_attachment_zip_builds_from_export_manifest(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    source = tmp_path / "photo.jpg"
    source.write_bytes(b"fake-image")

    intake_evidence_file(source, case_id="case-zip", subject_id=55)

    export_manifest = build_review_gated_manifest(
        subject_id=55,
        gate_mode="approved_and_uncertain",
    )

    result = build_attachment_zip(
        export_manifest_name=Path(export_manifest["manifest_path"]).name,
        case_id="case-zip",
        subject_id=55,
    )

    zip_path = Path(result["zip_path"])
    assert zip_path.exists()
    assert result["attachment_count"] == 1

    with zipfile.ZipFile(zip_path) as zf:
        names = set(zf.namelist())
        assert "README.txt" in names
        assert any(name.startswith("evidence/") for name in names)
        assert any(name.endswith("-ATTACHMENTS.json") for name in names)


def test_evidence_routes_registered():
    app = create_app()
    rules = {rule.rule for rule in app.url_map.iter_rules()}

    assert "/evidence/intake" in rules
    assert "/api/v1/evidence/intake" in rules
    assert "/evidence/intake/add" in rules
    assert "/evidence/intake/files/<path:name>/download" in rules
    assert "/api/v1/reports/export-center/attachments" in rules
    assert "/api/v1/reports/export-center/attachments/zip" in rules
