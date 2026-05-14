from __future__ import annotations

import base64

from socmint.dashboard import create_app
from socmint.dossier_finalization_certificate_handoff_index_v7_5_7 import build_handoff_index
from socmint.dossier_finalization_handoff_export_bundle_v7_5_8 import build_handoff_export_bundle
from socmint.dossier_finalization_handoff_export_bundle_v7_5_8 import build_handoff_export_zip
from socmint.dossier_finalization_handoff_export_verify_routes_v7_5_9 import register_dossier_finalization_handoff_export_verify_routes

CSRF_TOKEN = "test-csrf-token"
CSRF_HEADERS = {"X-CSRF-Token": CSRF_TOKEN}


def verified_report():
    return {
        "schema": "socmint.v7_5_6.dossier_finalization_certificate_bundle_verification",
        "status": "verified",
        "verified": True,
        "failure_count": 0,
        "warning_count": 0,
        "certificate_status": "valid",
        "certificate_valid": True,
        "required_files": ["handoff_index.json", "manifest.json"],
        "present_files": ["handoff_index.json", "manifest.json"],
        "missing_files": [],
        "unexpected_files": [],
        "manifest": {"files": [{"path": "handoff_index.json", "content_type": "application/json", "size_bytes": 123, "sha256": "a" * 64}]},
        "file_results": [{"path": "handoff_index.json", "hash_match": True, "size_match": True}],
        "failures": [],
        "warnings": [],
        "summary": {"status": "verified", "verified": True},
    }


def archive_bundle():
    index = build_handoff_index(verified_report(), bundle_name="bundle-a", operator="analyst")
    return build_handoff_export_bundle(index, bundle_name="handoff-export")


def app_client():
    app = create_app()
    register_dossier_finalization_handoff_export_verify_routes(app)
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
        "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/handoff-index/export/verify",
        {"bundle": archive_bundle()},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["schema"] == "socmint.v7_5_9.dossier_finalization_handoff_export_verification"
    assert data["status"] == "verified"
    assert data["verified"] is True


def test_raw_bundle_request_shape_works():
    client = app_client()
    response = post_json(client, "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/handoff-index/export/verify", archive_bundle())

    assert response.status_code == 200
    assert response.get_json()["status"] == "verified"


def test_wrapped_bundle_request_shape_works():
    client = app_client()
    response = post_json(
        client,
        "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/handoff-index/export/verify",
        {"bundle": archive_bundle()},
    )

    assert response.status_code == 200
    assert response.get_json()["summary"]["status"] == "verified"


def test_zip_base64_route_returns_verified_report():
    zip_bytes = build_handoff_export_zip(archive_bundle())
    encoded = base64.b64encode(zip_bytes).decode("ascii")
    client = app_client()
    response = post_json(
        client,
        "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/handoff-index/export/verify-zip",
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
        "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/handoff-index/export/verify-zip",
        {"zip_base64": "not base64!!!"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "failed"
    assert data["verified"] is False
    assert any(item["code"] == "invalid_zip" for item in data["failures"])


def test_missing_base64_returns_failed_report_not_500():
    client = app_client()
    response = post_json(client, "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/handoff-index/export/verify-zip", {})

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "failed"
    assert data["failure_count"] == 1


def test_no_connector_execution_function_is_called(monkeypatch):
    import socmint.dossier_finalization_handoff_export_verify_v7_5_9 as verify_module

    def explode(*_args, **_kwargs):
        raise AssertionError("connector execution must not happen")

    monkeypatch.setattr(verify_module, "execute_connector", explode, raising=False)
    client = app_client()
    response = post_json(client, "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/handoff-index/export/verify", {"bundle": archive_bundle()})

    assert response.status_code == 200
    assert response.get_json()["status"] == "verified"
