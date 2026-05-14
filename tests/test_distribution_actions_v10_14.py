import pytest

from src.socmint.distribution_action_routes import register_distribution_action_routes
from src.socmint.distribution_actions import distribution_action_markdown
from src.socmint.distribution_actions import distribution_action_packet
from src.socmint.distribution_actions import distribution_action_summary
from src.socmint.distribution_actions import record_distribution_action
from src.socmint.dossier_export_store import persist_export_pack
from src.socmint.wsgi import app


def _subject(subject_id="subject-dist-action-1", case_id="case-dist-action-1014"):
    return {
        "subject_id": subject_id,
        "display_name": "Distribution Action Subject",
        "case_id": case_id,
        "aliases": ["dist-action"],
    }


def _evidence():
    return [
        {
            "evidence_id": "ev-dist-action-1",
            "label": "profile artifact",
            "source": "public_profile",
            "confidence": 0.97,
            "artifact_id": "art-dist-action-1",
        }
    ]


def test_v10_14_records_review_and_approval_for_certified_export(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    persist_export_pack(_subject("subject-dist-action-safe"), _evidence(), analyst_reviewed=True, audit=True)

    review = record_distribution_action(
        case_id="case-dist-action-1014",
        subject_id="subject-dist-action-safe",
        action="mark_reviewed",
        actor="analyst",
        note="reviewed for release",
    )
    approval = record_distribution_action(
        case_id="case-dist-action-1014",
        subject_id="subject-dist-action-safe",
        action="approve",
        actor="analyst",
        note="approved for distribution",
    )
    summary = distribution_action_summary("case-dist-action-1014", "subject-dist-action-safe")
    packet = distribution_action_packet("case-dist-action-1014", "subject-dist-action-safe")

    assert review["action"] == "mark_reviewed"
    assert approval["action"] == "approve"
    assert approval["safe_to_distribute"] is True
    assert summary["event_count"] == 2
    assert summary["reviewed"] is True
    assert summary["approved"] is True
    assert packet["distribution_ready"] is True
    assert packet["recommended_bundle"].endswith("manifest.json")


def test_v10_14_blocks_approval_when_certification_blockers_remain(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    persist_export_pack(_subject("subject-dist-action-held"), _evidence(), analyst_reviewed=True, audit=False)

    with pytest.raises(ValueError, match="Cannot approve distribution"):
        record_distribution_action(
            case_id="case-dist-action-1014",
            subject_id="subject-dist-action-held",
            action="approve",
            actor="analyst",
        )

    hold = record_distribution_action(
        case_id="case-dist-action-1014",
        subject_id="subject-dist-action-held",
        action="hold",
        actor="analyst",
        note="audit coverage missing",
    )
    summary = distribution_action_summary("case-dist-action-1014", "subject-dist-action-held")

    assert hold["action"] == "hold"
    assert "audit_coverage" in hold["blockers"]
    assert summary["held"] is True
    assert summary["approved"] is False


def test_v10_14_reject_action_and_markdown_packet(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    persist_export_pack(_subject("subject-dist-action-reject"), _evidence(), analyst_reviewed=True, audit=True)

    record_distribution_action(
        case_id="case-dist-action-1014",
        subject_id="subject-dist-action-reject",
        action="reject",
        actor="analyst",
        note="wrong recipient",
    )
    markdown = distribution_action_markdown("case-dist-action-1014", "subject-dist-action-reject")

    assert "Distribution Action Packet" in markdown
    assert "Operator approved: False" in markdown
    assert "wrong recipient" in markdown
    assert "reject" in markdown


def test_v10_14_rejects_unknown_action(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    persist_export_pack(_subject("subject-dist-action-invalid"), _evidence(), analyst_reviewed=True, audit=True)

    with pytest.raises(ValueError, match="Unsupported distribution action"):
        record_distribution_action(
            case_id="case-dist-action-1014",
            subject_id="subject-dist-action-invalid",
            action="ship_now",
            actor="analyst",
        )


def test_v10_14_distribution_routes_are_registered():
    routes = {rule.rule for rule in app.url_map.iter_rules()}

    assert "/api/v1/dossier-builder/v3/distribution-actions/<case_id>/<subject_id>" in routes
    assert "/api/v1/dossier-builder/v3/distribution-packet/<case_id>/<subject_id>" in routes
    assert "/api/v1/dossier-builder/v3/distribution-packet/<case_id>/<subject_id>/markdown" in routes


def test_v10_14_distribution_action_api_requires_login():
    client = app.test_client()
    response = client.get("/api/v1/dossier-builder/v3/distribution-actions/case/subject")

    assert response.status_code == 401


def test_v10_14_distribution_route_registrar_returns_app():
    assert register_distribution_action_routes(app) is app
