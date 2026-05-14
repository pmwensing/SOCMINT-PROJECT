from src.socmint.distribution_actions import record_distribution_action
from src.socmint.distribution_packet_export import build_distribution_packet_export
from src.socmint.distribution_release_ledger import create_distribution_release_seal
from src.socmint.distribution_release_ledger import release_ledger_summary
from src.socmint.distribution_release_ledger import release_seal_markdown
from src.socmint.distribution_release_ledger import release_state
from src.socmint.dossier_export_store import persist_export_pack
from src.socmint.wsgi import app

import pytest


def _subject(subject_id="subject-release-ledger-1", case_id="case-release-ledger-1017"):
    return {
        "subject_id": subject_id,
        "display_name": "Release Ledger Subject",
        "case_id": case_id,
        "aliases": ["release-ledger"],
    }


def _evidence():
    return [
        {
            "evidence_id": "ev-release-ledger-1",
            "label": "profile artifact",
            "source": "public_profile",
            "confidence": 0.97,
            "artifact_id": "art-release-ledger-1",
        }
    ]


def _verified_export(tmp_path, monkeypatch, subject_id="subject-release-ledger-safe"):
    monkeypatch.chdir(tmp_path)
    persist_export_pack(_subject(subject_id), _evidence(), analyst_reviewed=True, audit=True)
    record_distribution_action(
        case_id="case-release-ledger-1017",
        subject_id=subject_id,
        action="mark_reviewed",
        actor="analyst",
        note="reviewed",
    )
    record_distribution_action(
        case_id="case-release-ledger-1017",
        subject_id=subject_id,
        action="approve",
        actor="analyst",
        note="approved",
    )
    build_distribution_packet_export("case-release-ledger-1017", subject_id)
    return subject_id


def test_v10_17_creates_release_seal_after_verification_passes(tmp_path, monkeypatch):
    subject_id = _verified_export(tmp_path, monkeypatch)

    seal = create_distribution_release_seal(
        case_id="case-release-ledger-1017",
        subject_id=subject_id,
        actor="analyst",
        note="final release",
    )
    state = release_state("case-release-ledger-1017", subject_id)

    assert seal["schema"] == "socmint.distribution_release_ledger.v10_17_0"
    assert seal["release_state"] == "released"
    assert seal["seal_id"]
    assert seal["zip_sha256"]
    assert seal["verification_status"] == "pass"
    assert state["sealed"] is True
    assert state["release_state"] == "released"
    assert state["seal"]["seal_id"] == seal["seal_id"]


def test_v10_17_blocks_seal_when_verification_missing_or_fails(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValueError, match="verification passes"):
        create_distribution_release_seal(
            case_id="case-release-ledger-1017",
            subject_id="missing-subject",
            actor="analyst",
        )

    state = release_state("case-release-ledger-1017", "missing-subject")
    assert state["sealed"] is False
    assert state["release_state"] == "held"


def test_v10_17_release_state_ready_to_seal_before_seal(tmp_path, monkeypatch):
    subject_id = _verified_export(tmp_path, monkeypatch, "subject-release-ledger-ready")

    state = release_state("case-release-ledger-1017", subject_id)

    assert state["sealed"] is False
    assert state["release_state"] == "ready_to_seal"
    assert state["verification"]["verified"] is True


def test_v10_17_ledger_summary_lists_released_subjects(tmp_path, monkeypatch):
    subject_id = _verified_export(tmp_path, monkeypatch, "subject-release-ledger-summary")
    seal = create_distribution_release_seal(
        case_id="case-release-ledger-1017",
        subject_id=subject_id,
        actor="analyst",
    )

    summary = release_ledger_summary("case-release-ledger-1017")

    assert summary["release_count"] == 1
    assert subject_id in summary["released_subjects"]
    assert summary["entries"][0]["seal_id"] == seal["seal_id"]


def test_v10_17_release_seal_markdown_contains_seal_fields(tmp_path, monkeypatch):
    subject_id = _verified_export(tmp_path, monkeypatch, "subject-release-ledger-md")
    seal = create_distribution_release_seal(
        case_id="case-release-ledger-1017",
        subject_id=subject_id,
        actor="analyst",
    )

    markdown = release_seal_markdown("case-release-ledger-1017", subject_id)

    assert "Distribution Release Seal" in markdown
    assert "Release state: released" in markdown
    assert seal["seal_id"] in markdown
    assert seal["zip_sha256"] in markdown


def test_v10_17_release_ledger_routes_are_registered():
    routes = {rule.rule for rule in app.url_map.iter_rules()}

    assert "/api/v1/dossier-builder/v3/distribution-release/<case_id>/<subject_id>/seal" in routes
    assert "/api/v1/dossier-builder/v3/distribution-release/<case_id>/<subject_id>" in routes
    assert "/api/v1/dossier-builder/v3/distribution-release/<case_id>/<subject_id>/markdown" in routes
    assert "/api/v1/dossier-builder/v3/distribution-release-ledger/<case_id>" in routes


def test_v10_17_release_state_api_requires_login():
    client = app.test_client()
    response = client.get("/api/v1/dossier-builder/v3/distribution-release/case/subject")

    assert response.status_code == 401
