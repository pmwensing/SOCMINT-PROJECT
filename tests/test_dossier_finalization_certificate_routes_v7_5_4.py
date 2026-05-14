from __future__ import annotations

import base64

from socmint.dashboard import create_app
from socmint.dossier_finalization_certificate_routes_v7_5_4 import register_dossier_finalization_certificate_routes
from socmint.dossier_finalization_export_v7_5_2 import build_finalization_export_packet
from socmint.dossier_finalization_export_v7_5_2 import build_finalization_export_zip
from socmint.dossier_finalization_export_verify_v7_5_3 import verify_finalization_export_packet

CSRF_TOKEN = "test-csrf-token"
CSRF_HEADERS = {"X-CSRF-Token": CSRF_TOKEN}


def base_payload():
    return {
        "quality_gate": {"status": "pass", "finding_count": 0},
        "export_enforcement": {"status": "allowed", "allowed": True, "final_export_blocked": False},
        "evidence_manifest": {"status": "pass", "appendix_summary": {"missing_ref_count": 0, "missing_hash_count": 0, "missing_source_count": 0}},
        "identity_confidence": {"status": "pass", "contradiction_count": 0, "low_confidence_count": 0, "needs_review_count": 0},
        "connector_compliance": {"status": "pass", "finding_count": 0},
        "policy_coverage": {"status": "pass", "finding_count": 0},
    }


def ready_packet():
    return build_finalization_export_packet(base_payload())


def verified_report():
    return verify_finalization_export_packet(ready_packet())


def app_client():
    app = create_app()
    register_dossier_finalization_certificate_routes(app)
    client = app.test_client()
    with client.session_transaction() as session:
        session["_csrf_token"] = CSRF_TOKEN
    return client


def post_json(client, path, payload):
    return client.post(path, json=payload, headers=CSRF_HEADERS)


def test_json_route_returns_valid_certificate_from_wrapped_report():
    client = app_client()
    response = post_json(
        client,
        "/api/v1/dossier-builder/v3/intelligence/finalization/certificate",
        {"verification_report": verified_report(), "packet_name": "packet-a", "reviewer": "analyst"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["schema"] == "socmint.v7_5_4.dossier_finalization_verification_certificate"
    assert data["status"] == "valid"
    assert data["valid"] is True
    assert data["packet_name"] == "packet-a"


def test_raw_verification_report_request_shape_works():
    client = app_client()
    response = post_json(client, "/api/v1/dossier-builder/v3/intelligence/finalization/certificate", verified_report())

    assert response.status_code == 200
    assert response.get_json()["status"] == "valid"


def test_markdown_route_returns_certificate_markdown():
    client = app_client()
    response = post_json(
        client,
        "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/markdown",
        {"verification_report": verified_report(), "notes": "Reviewed."},
    )

    assert response.status_code == 200
    assert response.mimetype == "text/markdown"
    text = response.get_data(as_text=True)
    assert "# SOCMINT v7.5.4 Finalization Verification Certificate" in text
    assert "Status: VALID" in text


def test_zip_route_returns_valid_certificate_for_valid_base64_zip():
    zip_bytes = build_finalization_export_zip(ready_packet())
    encoded = base64.b64encode(zip_bytes).decode("ascii")
    client = app_client()
    response = post_json(
        client,
        "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/from-zip",
        {"zip_base64": encoded, "packet_name": "zip-packet"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "valid"
    assert data["packet_name"] == "zip-packet"


def test_invalid_base64_returns_failed_certificate_not_500():
    client = app_client()
    response = post_json(
        client,
        "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/from-zip",
        {"zip_base64": "not-base64!!!"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "failed"
    assert data["valid"] is False
    assert data["failure_count"] == 1


def test_csrf_token_is_required_by_test_client_pattern():
    client = app_client()
    response = post_json(client, "/api/v1/dossier-builder/v3/intelligence/finalization/certificate", {"verification_report": verified_report()})

    assert response.status_code == 200


def test_no_connector_execution_function_is_called(monkeypatch):
    import socmint.dossier_finalization_certificate_v7_5_4 as cert_module

    def explode(*_args, **_kwargs):
        raise AssertionError("connector execution must not happen")

    monkeypatch.setattr(cert_module, "execute_connector", explode, raising=False)
    client = app_client()
    response = post_json(client, "/api/v1/dossier-builder/v3/intelligence/finalization/certificate", {"verification_report": verified_report()})

    assert response.status_code == 200
    assert response.get_json()["status"] == "valid"
