from src.socmint.distribution_actions import record_distribution_action
from src.socmint.distribution_packet_export import build_distribution_packet_export
from src.socmint.distribution_release_ledger import create_distribution_release_seal
from src.socmint.dossier_export_store import persist_export_pack
from src.socmint.release_ledger_dashboard import release_ledger_dashboard
from src.socmint.release_ledger_dashboard import release_ledger_dashboard_markdown
from src.socmint.wsgi import app


def _subject(subject_id="subject-ledger-dashboard-1", case_id="case-ledger-dashboard-1018"):
    return {
        "subject_id": subject_id,
        "display_name": "Ledger Dashboard Subject",
        "case_id": case_id,
        "aliases": ["ledger-dashboard"],
    }


def _evidence():
    return [
        {
            "evidence_id": "ev-ledger-dashboard-1",
            "label": "profile artifact",
            "source": "public_profile",
            "confidence": 0.97,
            "artifact_id": "art-ledger-dashboard-1",
        }
    ]


def _approved_export(subject_id: str):
    persist_export_pack(_subject(subject_id), _evidence(), analyst_reviewed=True, audit=True)
    record_distribution_action(
        case_id="case-ledger-dashboard-1018",
        subject_id=subject_id,
        action="mark_reviewed",
        actor="analyst",
        note="reviewed",
    )
    record_distribution_action(
        case_id="case-ledger-dashboard-1018",
        subject_id=subject_id,
        action="approve",
        actor="analyst",
        note="approved",
    )
    build_distribution_packet_export("case-ledger-dashboard-1018", subject_id)


def test_v10_18_dashboard_counts_released_ready_and_held(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _approved_export("subject-ledger-dashboard-released")
    create_distribution_release_seal(
        case_id="case-ledger-dashboard-1018",
        subject_id="subject-ledger-dashboard-released",
        actor="analyst",
    )
    _approved_export("subject-ledger-dashboard-ready")
    persist_export_pack(_subject("subject-ledger-dashboard-held"), _evidence(), analyst_reviewed=True, audit=False)

    payload = release_ledger_dashboard("case-ledger-dashboard-1018")

    assert payload["schema"] == "socmint.release_ledger_dashboard.v10_18_0"
    assert payload["export_count"] == 3
    assert payload["counts"]["released"] == 1
    assert payload["counts"]["ready_to_seal"] == 1
    assert payload["counts"]["held"] == 1
    states = {row["subject_id"]: row["release_state"] for row in payload["rows"]}
    assert states["subject-ledger-dashboard-released"] == "released"
    assert states["subject-ledger-dashboard-ready"] == "ready_to_seal"
    assert states["subject-ledger-dashboard-held"] == "held"


def test_v10_18_dashboard_rows_include_seal_and_zip_fields(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _approved_export("subject-ledger-dashboard-fields")
    seal = create_distribution_release_seal(
        case_id="case-ledger-dashboard-1018",
        subject_id="subject-ledger-dashboard-fields",
        actor="analyst",
    )

    payload = release_ledger_dashboard("case-ledger-dashboard-1018")
    row = payload["rows"][0]

    assert row["seal_id"] == seal["seal_id"]
    assert row["zip_sha256"] == seal["zip_sha256"]
    assert row["verification_status"] == "pass"
    assert row["sealed"] is True


def test_v10_18_dashboard_markdown_contains_case_summary(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _approved_export("subject-ledger-dashboard-md")

    markdown = release_ledger_dashboard_markdown("case-ledger-dashboard-1018")

    assert "Release Ledger Dashboard" in markdown
    assert "Exports: 1" in markdown
    assert "Ready to seal: 1" in markdown
    assert "subject-ledger-dashboard-md" in markdown


def test_v10_18_release_ledger_dashboard_routes_are_registered():
    routes = {rule.rule for rule in app.url_map.iter_rules()}

    assert "/dossier/release-ledger-dashboard" in routes
    assert "/api/v1/dossier-builder/v3/release-ledger-dashboard/<case_id>" in routes
    assert "/api/v1/dossier-builder/v3/release-ledger-dashboard/<case_id>/markdown" in routes


def test_v10_18_release_ledger_dashboard_requires_login():
    client = app.test_client()
    response = client.get("/dossier/release-ledger-dashboard")

    assert response.status_code in {301, 302}
    assert "/login" in response.headers["Location"]


def test_v10_18_release_ledger_dashboard_renders_for_authenticated_user():
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user"] = "analyst"
        sess["role"] = "analyst"
        sess["is_admin"] = False

    response = client.get("/dossier/release-ledger-dashboard")

    assert response.status_code == 200
    assert b"Release Ledger Dashboard / Case Distribution Console" in response.data
    assert b"No case selected" in response.data


def test_v10_18_release_ledger_dashboard_api_requires_login():
    client = app.test_client()
    response = client.get("/api/v1/dossier-builder/v3/release-ledger-dashboard/case")

    assert response.status_code == 401
