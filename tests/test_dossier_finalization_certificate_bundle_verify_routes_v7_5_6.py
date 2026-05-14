from __future__ import annotations

import base64

from socmint.dashboard import create_app
from socmint.dossier_finalization_certificate_bundle_routes_v7_5_5 import build_certificate_bundle_zip
from socmint.dossier_finalization_certificate_bundle_v7_5_5 import build_certificate_bundle
from socmint.dossier_finalization_certificate_bundle_verify_routes_v7_5_6 import register_dossier_finalization_certificate_bundle_verify_routes
from socmint.dossier_finalization_certificate_v7_5_4 import build_verification_certificate

CSRF_TOKEN = "test-csrf-token"
CSRF_HEADERS = {"X-CSRF-Token": CSRF_TOKEN}


def verified_report():
    return {
        "schema": "socmint.v7_5_3.dossier_finalization_export_verification",
        "status": "verified",
        "verified": True,
        "failure_count": 0,
        "warning_count": 0,
        "required_files": ["manifest.json"],
        "present_files": ["manifest.json"],
        "missing_files": [],
        "unexpected_files": [],
        "failures": [],
        "warnings": [],
        "summary": {"status": "verified", "verified": True},
    }


def valid_bundle():
    certificate = build_verification_certificate(verified_report(), packet_name="packet-a")
    return build_certificate_bundle(certificate, bundle_name="bundle-a")


def app_client():
    app = create_app()
    register_dossier_finalization_certificate_bundle_verify_routes(app)
    client = app.test_client()
    with client.session_transaction() as session:
        session["_csrf_token"] = CSRF_TOKEN
    return client


def post_json(client, path, payload):
    return client.post(path, json=payload, headers=CSRF_HEADERS)


def test_json_bundle_route_returns_verified_report():
    client = app_client()
    response = post_json(
        client,
        "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/bundle/verify",
        {"bundle": valid_bundle()},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["schema"] == "socmint.v7_5_6.dossier_finalization_certificate_bundle_verification"
    assert data["status"] == "verified"
    assert data["verified"] is True


def test_raw_bundle_request_shape_works():
    client = app_client()
    response = post_json(client, "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/bundle/verify", valid_bundle())

    assert response.status_code == 200
    assert response.get_json()["status"] == "verified"


def test_wrapped_bundle_request_shape_works():
    client = app_client()
    response = post_json(
        client,
        "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/bundle/verify",
        {"bundle": valid_bundle()},
    )

    assert response.status_code == 200
    assert response.get_json()["summary"]["status"] == "verified"


def test_zip_base64_route_returns_verified_report():
    zip_bytes = build_certificate_bundle_zip(valid_bundle())
    encoded = base64.b64encode(zip_bytes).decode("ascii")
    client = app_client()
    response = post_json(
        client,
        "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/bundle/verify-zip",
        {"zip_base64": encoded},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "verified"
    assert data["verified"] is True


def test_invalid_base64_returns_failed_report_not_500():
    client = app_client()
    response = post_json(
        client,
        "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/bundle/verify-zip",
        {"zip_base64": "not base64!!!"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "failed"
    assert data["verified"] is False
    assert any(item["code"] == "invalid_zip" for item in data["failures"])


def test_missing_base64_returns_failed_report_not_500():
    client = app_client()
    response = post_json(client, "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/bundle/verify-zip", {})

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "failed"
    assert data["failure_count"] == 1


def test_no_connector_execution_function_is_called(monkeypatch):
    import socmint.dossier_finalization_certificate_bundle_verify_v7_5_6 as verify_module

    def explode(*_args, **_kwargs):
        raise AssertionError("connector execution must not happen")

    monkeypatch.setattr(verify_module, "execute_connector", explode, raising=False)
    client = app_client()
    response = post_json(client, "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/bundle/verify", {"bundle": valid_bundle()})

    assert response.status_code == 200
    assert response.get_json()["status"] == "verified"
