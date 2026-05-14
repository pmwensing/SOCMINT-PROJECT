from src.socmint.certification_dashboard_routes import _dashboard_payload
from src.socmint.dossier_export_store import persist_export_pack
from src.socmint.wsgi import app


def _subject(subject_id="subject-cert-ui-1", case_id="case-cert-ui-1013"):
    return {
        "subject_id": subject_id,
        "display_name": "Certification UI Subject",
        "case_id": case_id,
        "aliases": ["cert-ui"],
    }


def _evidence():
    return [
        {
            "evidence_id": "ev-cert-ui-1",
            "label": "profile artifact",
            "source": "public_profile",
            "confidence": 0.97,
            "artifact_id": "art-cert-ui-1",
        }
    ]


def test_v10_13_dashboard_payload_empty_without_case():
    payload = _dashboard_payload(case_id=None)

    assert payload["status"] == "empty"
    assert payload["index"] is None
    assert payload["summary"] is None
    assert payload["markdown"] == ""


def test_v10_13_dashboard_payload_summarizes_case_exports(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    persist_export_pack(_subject("subject-cert-ui-safe"), _evidence(), analyst_reviewed=True, audit=True)
    persist_export_pack(_subject("subject-cert-ui-held"), _evidence(), analyst_reviewed=True, audit=False)

    payload = _dashboard_payload(case_id="case-cert-ui-1013")

    assert payload["status"] == "ready"
    assert payload["summary"]["export_count"] == 2
    assert payload["summary"]["safe_to_distribute_count"] == 1
    assert payload["summary"]["hold_count"] == 1
    assert "Certification Index — case-cert-ui-1013" in payload["markdown"]


def test_v10_13_dashboard_payload_focuses_subject(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    persist_export_pack(_subject("subject-cert-ui-focus"), _evidence(), analyst_reviewed=True, audit=True)

    payload = _dashboard_payload(case_id="case-cert-ui-1013", subject_id="subject-cert-ui-focus")

    assert payload["entry"]["subject_id"] == "subject-cert-ui-focus"
    assert payload["entry"]["safe_to_distribute"] is True
    assert payload["entry"]["artifact_count"] == 2


def test_v10_13_dashboard_routes_are_registered():
    routes = {rule.rule for rule in app.url_map.iter_rules()}

    assert "/dossier/certification-dashboard" in routes
    assert "/api/v1/dossier-builder/v3/certification-dashboard/<case_id>" in routes


def test_v10_13_dashboard_redirects_anonymous_user():
    client = app.test_client()
    response = client.get("/dossier/certification-dashboard")

    assert response.status_code in {301, 302}
    assert "/login" in response.headers["Location"]


def test_v10_13_dashboard_renders_for_authenticated_user():
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user"] = "analyst"
        sess["role"] = "analyst"
        sess["is_admin"] = False

    response = client.get("/dossier/certification-dashboard")

    assert response.status_code == 200
    assert b"Certification Index UI / Distribution Readiness Dashboard" in response.data
    assert b"No case selected" in response.data
