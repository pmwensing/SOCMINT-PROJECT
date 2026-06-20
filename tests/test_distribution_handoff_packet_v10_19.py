from src.socmint.distribution_actions import record_distribution_action
from src.socmint.distribution_handoff_packet import distribution_handoff_markdown
from src.socmint.distribution_handoff_packet import distribution_handoff_packet
from src.socmint.distribution_packet_export import build_distribution_packet_export
from src.socmint.distribution_release_ledger import create_distribution_release_seal
from src.socmint.dossier_export_store import persist_export_pack
from src.socmint.wsgi import app


def _subject(subject_id="subject-handoff-1", case_id="case-handoff-1019"):
    return {
        "subject_id": subject_id,
        "display_name": "Handoff Subject",
        "case_id": case_id,
        "aliases": ["handoff"],
    }


def _evidence():
    return [
        {
            "evidence_id": "ev-handoff-1",
            "label": "profile artifact",
            "source": "public_profile",
            "confidence": 0.97,
            "artifact_id": "art-handoff-1",
        }
    ]


def _approved_export(subject_id: str):
    persist_export_pack(
        _subject(subject_id), _evidence(), analyst_reviewed=True, audit=True
    )
    record_distribution_action(
        case_id="case-handoff-1019",
        subject_id=subject_id,
        action="mark_reviewed",
        actor="analyst",
        note="reviewed",
    )
    record_distribution_action(
        case_id="case-handoff-1019",
        subject_id=subject_id,
        action="approve",
        actor="analyst",
        note="approved",
    )
    build_distribution_packet_export("case-handoff-1019", subject_id)


def test_v10_19_handoff_packet_summarizes_released_ready_and_held(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    _approved_export("subject-handoff-released")
    seal = create_distribution_release_seal(
        case_id="case-handoff-1019",
        subject_id="subject-handoff-released",
        actor="analyst",
    )
    _approved_export("subject-handoff-ready")
    persist_export_pack(
        _subject("subject-handoff-held"),
        _evidence(),
        analyst_reviewed=True,
        audit=False,
    )

    packet = distribution_handoff_packet("case-handoff-1019")

    assert packet["schema"] == "socmint.distribution_handoff_packet.v10_19_0"
    assert packet["export_count"] == 3
    assert packet["release_count"] == 1
    assert packet["released_count"] == 1
    assert packet["ready_to_seal_count"] == 1
    assert packet["held_count"] == 1
    rows = {row["subject_id"]: row for row in packet["subjects"]}
    assert rows["subject-handoff-released"]["seal_id"] == seal["seal_id"]
    assert rows["subject-handoff-released"]["verification_status"] == "pass"
    assert rows["subject-handoff-ready"]["release_state"] == "ready_to_seal"
    assert rows["subject-handoff-held"]["release_state"] == "held"


def test_v10_19_handoff_packet_includes_operator_links(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _approved_export("subject-handoff-links")

    packet = distribution_handoff_packet("case-handoff-1019")
    row = packet["subjects"][0]

    assert row["download_url"].endswith(
        "/distribution-export/case-handoff-1019/subject-handoff-links/download"
    )
    assert row["verify_url"].endswith(
        "/distribution-export/case-handoff-1019/subject-handoff-links/verify"
    )
    assert row["release_state_url"].endswith(
        "/distribution-release/case-handoff-1019/subject-handoff-links"
    )
    assert row["seal_markdown_url"].endswith(
        "/distribution-release/case-handoff-1019/subject-handoff-links/markdown"
    )


def test_v10_19_handoff_markdown_contains_summary_and_seal_statement(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    _approved_export("subject-handoff-md")
    seal = create_distribution_release_seal(
        case_id="case-handoff-1019",
        subject_id="subject-handoff-md",
        actor="analyst",
    )

    markdown = distribution_handoff_markdown("case-handoff-1019")

    assert "Release Distribution Handoff Packet" in markdown
    assert "Exports: 1" in markdown
    assert "Released: 1" in markdown
    assert "subject-handoff-md" in markdown
    assert seal["seal_id"] in markdown
    assert "Distribution Release Seal" in markdown


def test_v10_19_handoff_routes_are_registered():
    routes = {rule.rule for rule in app.url_map.iter_rules()}

    assert "/api/v1/dossier-builder/v3/distribution-handoff/<case_id>" in routes
    assert (
        "/api/v1/dossier-builder/v3/distribution-handoff/<case_id>/markdown" in routes
    )


def test_v10_19_handoff_api_requires_login():
    client = app.test_client()
    response = client.get("/api/v1/dossier-builder/v3/distribution-handoff/case")

    assert response.status_code == 401


def test_v10_19_release_dashboard_exposes_handoff_links():
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user"] = "analyst"
        sess["role"] = "analyst"
        sess["is_admin"] = False

    response = client.get("/dossier/release-ledger-dashboard?case_id=case-handoff-1019")

    assert response.status_code == 200
    assert b"Handoff JSON" in response.data
    assert b"Handoff markdown" in response.data
