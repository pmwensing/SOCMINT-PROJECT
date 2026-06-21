from __future__ import annotations

import base64

from socmint.dashboard import create_app
from socmint.dossier_finalization_certificate_bundle_v7_5_5 import (
    build_certificate_bundle,
)
from socmint.dossier_finalization_certificate_bundle_v7_5_5 import (
    build_certificate_bundle_zip,
)
from socmint.dossier_finalization_certificate_handoff_index_routes_v7_5_7 import (
    register_dossier_finalization_certificate_handoff_index_routes,
)
from socmint.dossier_finalization_certificate_v7_5_4 import (
    build_verification_certificate,
)
from socmint.dossier_finalization_certificate_bundle_verify_v7_5_6 import (
    verify_certificate_bundle,
)

CSRF_TOKEN = "test-csrf-token"
CSRF_HEADERS = {"X-CSRF-Token": CSRF_TOKEN}


def base_v753_report():
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
    certificate = build_verification_certificate(
        base_v753_report(), packet_name="packet-a"
    )
    return build_certificate_bundle(certificate, bundle_name="bundle-a")


def verified_report():
    return verify_certificate_bundle(valid_bundle())


def app_client():
    app = create_app()
    register_dossier_finalization_certificate_handoff_index_routes(app)
    client = app.test_client()
    with client.session_transaction() as session:
        session["_csrf_token"] = CSRF_TOKEN
    return client


def post_json(client, path, payload):
    return client.post(path, json=payload, headers=CSRF_HEADERS)


def test_json_route_returns_archive_ready_index_from_wrapped_report():
    client = app_client()
    response = post_json(
        client,
        "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/handoff-index",
        {
            "verification_report": verified_report(),
            "bundle_name": "bundle-a",
            "operator": "analyst",
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert (
        data["schema"]
        == "socmint.v7_5_7.dossier_finalization_certificate_handoff_index"
    )
    assert data["recommended_action"] == "archive_ready"
    assert data["operator"] == "analyst"


def test_raw_verification_report_request_shape_works():
    client = app_client()
    response = post_json(
        client,
        "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/handoff-index",
        verified_report(),
    )

    assert response.status_code == 200
    assert response.get_json()["recommended_action"] == "archive_ready"


def test_markdown_route_returns_handoff_index_markdown():
    client = app_client()
    response = post_json(
        client,
        "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/handoff-index/markdown",
        {"verification_report": verified_report(), "notes": "Ready."},
    )

    assert response.status_code == 200
    assert response.mimetype == "text/markdown"
    text = response.get_data(as_text=True)
    assert "# SOCMINT v7.5.7 Certificate Bundle Handoff Index" in text
    assert "Recommended action: ARCHIVE READY" in text


def test_zip_route_returns_archive_ready_index_for_valid_base64_zip():
    zip_bytes = build_certificate_bundle_zip(valid_bundle())
    encoded = base64.b64encode(zip_bytes).decode("ascii")
    client = app_client()
    response = post_json(
        client,
        "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/handoff-index/from-zip",
        {"zip_base64": encoded, "bundle_name": "zip-bundle"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["recommended_action"] == "archive_ready"
    assert data["bundle_name"] == "zip-bundle"


def test_invalid_base64_returns_regenerate_bundle_index_not_500():
    client = app_client()
    response = post_json(
        client,
        "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/handoff-index/from-zip",
        {"zip_base64": "not base64!!!"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["recommended_action"] == "regenerate_bundle"
    assert data["verification_status"] == "failed"


def test_csrf_token_is_used_in_route_tests():
    client = app_client()
    response = post_json(
        client,
        "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/handoff-index",
        {"verification_report": verified_report()},
    )

    assert response.status_code == 200


def test_no_connector_execution_function_is_called(monkeypatch):
    import socmint.dossier_finalization_certificate_handoff_index_v7_5_7 as index_module

    def explode(*_args, **_kwargs):
        raise AssertionError("connector execution must not happen")

    monkeypatch.setattr(index_module, "execute_connector", explode, raising=False)
    client = app_client()
    response = post_json(
        client,
        "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/handoff-index",
        {"verification_report": verified_report()},
    )

    assert response.status_code == 200
    assert response.get_json()["recommended_action"] == "archive_ready"
