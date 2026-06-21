from __future__ import annotations

import io
import zipfile

from socmint.dashboard import create_app
from socmint.dossier_finalization_certificate_bundle_routes_v7_5_5 import (
    register_dossier_finalization_certificate_bundle_routes,
)
from socmint.dossier_finalization_certificate_v7_5_4 import (
    build_verification_certificate,
)

CSRF_TOKEN = "test-csrf-token"
CSRF_HEADERS = {"X-CSRF-Token": CSRF_TOKEN}
REQUIRED_FILES = {
    "README.md",
    "certificate.json",
    "certificate.md",
    "certificate_summary.json",
    "manifest.json",
}


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


def valid_certificate():
    return build_verification_certificate(verified_report(), packet_name="packet-a")


def app_client():
    app = create_app()
    register_dossier_finalization_certificate_bundle_routes(app)
    client = app.test_client()
    with client.session_transaction() as session:
        session["_csrf_token"] = CSRF_TOKEN
    return client


def post_json(client, path, payload):
    return client.post(path, json=payload, headers=CSRF_HEADERS)


def test_json_route_returns_bundle_metadata_from_wrapped_certificate():
    client = app_client()
    response = post_json(
        client,
        "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/bundle",
        {"certificate": valid_certificate(), "bundle_name": "Case Bundle"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["schema"] == "socmint.v7_5_5.dossier_finalization_certificate_bundle"
    assert data["bundle_name"] == "case-bundle"
    assert data["certificate_status"] == "valid"


def test_raw_certificate_request_shape_works():
    client = app_client()
    response = post_json(
        client,
        "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/bundle",
        valid_certificate(),
    )

    assert response.status_code == 200
    assert response.get_json()["certificate_status"] == "valid"


def test_zip_route_returns_application_zip():
    client = app_client()
    response = post_json(
        client,
        "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/bundle.zip",
        {"certificate": valid_certificate(), "bundle_name": "Case Bundle"},
    )

    assert response.status_code == 200
    assert response.mimetype == "application/zip"
    assert "case-bundle.zip" in response.headers["Content-Disposition"]


def test_zip_route_contains_required_files():
    client = app_client()
    response = post_json(
        client,
        "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/bundle.zip",
        {"certificate": valid_certificate()},
    )

    with zipfile.ZipFile(io.BytesIO(response.get_data())) as archive:
        assert set(archive.namelist()) == REQUIRED_FILES


def test_csrf_token_is_used_in_route_tests():
    client = app_client()
    response = post_json(
        client,
        "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/bundle",
        {"certificate": valid_certificate()},
    )

    assert response.status_code == 200


def test_no_connector_execution_function_is_called(monkeypatch):
    import socmint.dossier_finalization_certificate_bundle_v7_5_5 as bundle_module

    def explode(*_args, **_kwargs):
        raise AssertionError("connector execution must not happen")

    monkeypatch.setattr(bundle_module, "execute_connector", explode, raising=False)
    client = app_client()
    response = post_json(
        client,
        "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/bundle",
        {"certificate": valid_certificate()},
    )

    assert response.status_code == 200
    assert response.get_json()["certificate_status"] == "valid"
