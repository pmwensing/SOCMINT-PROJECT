from pathlib import Path
from zipfile import ZipFile

import pytest

from src.socmint.distribution_actions import record_distribution_action
from src.socmint.distribution_packet_export import build_distribution_packet_export
from src.socmint.distribution_packet_export import distribution_packet_export_summary
from src.socmint.dossier_export_store import persist_export_pack
from src.socmint.wsgi import app


def _subject(subject_id="subject-packet-export-1", case_id="case-packet-export-1015"):
    return {
        "subject_id": subject_id,
        "display_name": "Packet Export Subject",
        "case_id": case_id,
        "aliases": ["packet-export"],
    }


def _evidence():
    return [
        {
            "evidence_id": "ev-packet-export-1",
            "label": "profile artifact",
            "source": "public_profile",
            "confidence": 0.97,
            "artifact_id": "art-packet-export-1",
        }
    ]


def _approved_export(tmp_path, monkeypatch, subject_id="subject-packet-export-safe"):
    monkeypatch.chdir(tmp_path)
    persist_export_pack(_subject(subject_id), _evidence(), analyst_reviewed=True, audit=True)
    record_distribution_action(
        case_id="case-packet-export-1015",
        subject_id=subject_id,
        action="mark_reviewed",
        actor="analyst",
        note="reviewed",
    )
    record_distribution_action(
        case_id="case-packet-export-1015",
        subject_id=subject_id,
        action="approve",
        actor="analyst",
        note="approved",
    )
    return subject_id


def test_v10_15_builds_distribution_export_zip_for_approved_packet(tmp_path, monkeypatch):
    subject_id = _approved_export(tmp_path, monkeypatch)

    manifest = build_distribution_packet_export("case-packet-export-1015", subject_id)

    assert manifest["schema"] == "socmint.distribution_packet_export.v10_15_0"
    assert manifest["status"] == "ready"
    assert manifest["distribution_ready"] is True
    assert manifest["safe_to_distribute"] is True
    assert manifest["zip_sha256"]
    assert manifest["zip_size_bytes"] > 0
    assert Path(manifest["zip_path"]).exists()
    assert Path(manifest["manifest_path"]).exists()

    with ZipFile(manifest["zip_path"]) as archive:
        names = set(archive.namelist())

    assert "README.txt" in names
    assert "distribution_statement.md" in names
    assert "distribution_packet.json" in names
    assert "dossier_manifest.json" in names
    assert "operator_action_log.jsonl" in names
    assert "operator_action_summary.json" in names
    assert any(name.startswith("artifacts/") for name in names)


def test_v10_15_export_summary_reads_existing_manifest(tmp_path, monkeypatch):
    subject_id = _approved_export(tmp_path, monkeypatch, "subject-packet-export-summary")
    built = build_distribution_packet_export("case-packet-export-1015", subject_id)

    summary = distribution_packet_export_summary("case-packet-export-1015", subject_id)

    assert summary["status"] == "ready"
    assert summary["zip_path"] == built["zip_path"]
    assert summary["zip_sha256"] == built["zip_sha256"]


def test_v10_15_summary_reports_missing_before_build(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    summary = distribution_packet_export_summary("case-packet-export-1015", "missing-subject")

    assert summary["status"] == "missing"
    assert summary["case_id"] == "case-packet-export-1015"
    assert summary["subject_id"] == "missing-subject"


def test_v10_15_blocks_export_when_not_approved(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    persist_export_pack(_subject("subject-packet-export-no-approval"), _evidence(), analyst_reviewed=True, audit=True)

    with pytest.raises(ValueError, match="certified and approved"):
        build_distribution_packet_export("case-packet-export-1015", "subject-packet-export-no-approval")


def test_v10_15_blocks_export_when_certification_blockers_remain(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    persist_export_pack(_subject("subject-packet-export-held"), _evidence(), analyst_reviewed=True, audit=False)
    record_distribution_action(
        case_id="case-packet-export-1015",
        subject_id="subject-packet-export-held",
        action="hold",
        actor="analyst",
        note="audit missing",
    )

    with pytest.raises(ValueError, match="certified and approved"):
        build_distribution_packet_export("case-packet-export-1015", "subject-packet-export-held")


def test_v10_15_distribution_export_routes_are_registered():
    routes = {rule.rule for rule in app.url_map.iter_rules()}

    assert "/api/v1/dossier-builder/v3/distribution-export/<case_id>/<subject_id>/build" in routes
    assert "/api/v1/dossier-builder/v3/distribution-export/<case_id>/<subject_id>" in routes
    assert "/api/v1/dossier-builder/v3/distribution-export/<case_id>/<subject_id>/download" in routes


def test_v10_15_distribution_export_api_requires_login():
    client = app.test_client()
    response = client.get("/api/v1/dossier-builder/v3/distribution-export/case/subject")

    assert response.status_code == 401
