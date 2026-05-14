from pathlib import Path

from src.socmint.distribution_actions import record_distribution_action
from src.socmint.distribution_export_verification import distribution_export_verification_markdown
from src.socmint.distribution_export_verification import verify_distribution_export
from src.socmint.distribution_packet_export import build_distribution_packet_export
from src.socmint.dossier_export_store import persist_export_pack
from src.socmint.wsgi import app


def _subject(subject_id="subject-export-verify-1", case_id="case-export-verify-1016"):
    return {
        "subject_id": subject_id,
        "display_name": "Export Verify Subject",
        "case_id": case_id,
        "aliases": ["export-verify"],
    }


def _evidence():
    return [
        {
            "evidence_id": "ev-export-verify-1",
            "label": "profile artifact",
            "source": "public_profile",
            "confidence": 0.97,
            "artifact_id": "art-export-verify-1",
        }
    ]


def _built_export(tmp_path, monkeypatch, subject_id="subject-export-verify-safe"):
    monkeypatch.chdir(tmp_path)
    persist_export_pack(_subject(subject_id), _evidence(), analyst_reviewed=True, audit=True)
    record_distribution_action(
        case_id="case-export-verify-1016",
        subject_id=subject_id,
        action="mark_reviewed",
        actor="analyst",
        note="reviewed",
    )
    record_distribution_action(
        case_id="case-export-verify-1016",
        subject_id=subject_id,
        action="approve",
        actor="analyst",
        note="approved",
    )
    build_distribution_packet_export("case-export-verify-1016", subject_id)
    return subject_id


def test_v10_16_verifies_clean_distribution_export(tmp_path, monkeypatch):
    subject_id = _built_export(tmp_path, monkeypatch)

    result = verify_distribution_export("case-export-verify-1016", subject_id)

    assert result["schema"] == "socmint.distribution_export_verification.v10_16_0"
    assert result["status"] == "pass"
    assert result["verified"] is True
    assert result["blockers"] == []
    assert result["zip_status"]["required_missing"] == []
    assert result["zip_status"]["actual_artifact_count"] == result["zip_status"]["expected_artifact_count"]
    assert all(item["verified"] for item in result["file_checks"])


def test_v10_16_reports_missing_export_manifest(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = verify_distribution_export("case-export-verify-1016", "missing-subject")

    assert result["status"] == "missing"
    assert result["verified"] is False
    assert result["blockers"] == ["missing_distribution_export_manifest"]


def test_v10_16_detects_zip_hash_mismatch(tmp_path, monkeypatch):
    subject_id = _built_export(tmp_path, monkeypatch, "subject-export-verify-tamper")
    clean = verify_distribution_export("case-export-verify-1016", subject_id)
    zip_path = Path(clean["manifest"]["zip_path"])
    with zip_path.open("ab") as handle:
        handle.write(b"tamper")

    result = verify_distribution_export("case-export-verify-1016", subject_id)

    assert result["status"] == "fail"
    assert result["verified"] is False
    assert "zip_hash_mismatch" in result["blockers"]
    assert "zip_size_mismatch" in result["blockers"]


def test_v10_16_detects_missing_source_file(tmp_path, monkeypatch):
    subject_id = _built_export(tmp_path, monkeypatch, "subject-export-verify-missing-source")
    clean = verify_distribution_export("case-export-verify-1016", subject_id)
    artifact_check = next(item for item in clean["file_checks"] if item["role"] == "dossier_artifact")
    Path(artifact_check["path"]).unlink()

    result = verify_distribution_export("case-export-verify-1016", subject_id)

    assert result["status"] == "fail"
    assert result["verified"] is False
    assert "source_file_missing" in result["blockers"]


def test_v10_16_markdown_report_contains_status(tmp_path, monkeypatch):
    subject_id = _built_export(tmp_path, monkeypatch, "subject-export-verify-md")

    markdown = distribution_export_verification_markdown("case-export-verify-1016", subject_id)

    assert "Distribution Export Verification" in markdown
    assert "Status: pass" in markdown
    assert "Verified: True" in markdown
    assert "Blockers: none" in markdown


def test_v10_16_verification_routes_are_registered():
    routes = {rule.rule for rule in app.url_map.iter_rules()}

    assert "/api/v1/dossier-builder/v3/distribution-export/<case_id>/<subject_id>/verify" in routes
    assert "/api/v1/dossier-builder/v3/distribution-export/<case_id>/<subject_id>/verify/markdown" in routes


def test_v10_16_verification_api_requires_login():
    client = app.test_client()
    response = client.get("/api/v1/dossier-builder/v3/distribution-export/case/subject/verify")

    assert response.status_code == 401
