from __future__ import annotations

import io
import zipfile

from socmint.dashboard import create_app
from socmint.dossier_finalization_certificate_handoff_index_v7_5_7 import build_handoff_index
from socmint.dossier_finalization_handoff_export_bundle_routes_v7_5_8 import register_dossier_finalization_handoff_export_bundle_routes

CSRF_TOKEN = "test-csrf-token"
CSRF_HEADERS = {"X-CSRF-Token": CSRF_TOKEN}
REQUIRED_FILES = {
    "README.md",
    "handoff_index.json",
    "handoff_index.md",
    "handoff_index_summary.json",
    "manifest.json",
}


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


def archive_index():
    return build_handoff_index(verified_report(), bundle_name="bundle-a", operator="analyst")


def app_client():
    app = create_app()
    register_dossier_finalization_handoff_export_bundle_routes(app)
    client = app.test_client()
    with client.session_transaction() as session:
        session["_csrf_token"] = CSRF_TOKEN
    return client


def post_json(client, path, payload):
    return client.post(path, json=payload, headers=CSRF_HEADERS)


def test_json_route_returns_export_bundle_metadata_from_wrapped_index():
    client = app_client()
    response = post_json(
        client,
        "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/handoff-index/export",
        {"index": archive_index(), "bundle_name": "Handoff Bundle"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["schema"] == "socmint.v7_5_8.dossier_finalization_handoff_export_bundle"
    assert data["bundle_name"] == "handoff-bundle"
    assert data["recommended_action"] == "archive_ready"


def test_raw_index_request_shape_works():
    client = app_client()
    response = post_json(client, "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/handoff-index/export", archive_index())

    assert response.status_code == 200
    assert response.get_json()["recommended_action"] == "archive_ready"


def test_zip_route_returns_application_zip():
    client = app_client()
    response = post_json(
        client,
        "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/handoff-index/export.zip",
        {"index": archive_index(), "bundle_name": "Handoff Bundle"},
    )

    assert response.status_code == 200
    assert response.mimetype == "application/zip"
    assert "handoff-bundle.zip" in response.headers["Content-Disposition"]


def test_zip_route_contains_required_files():
    client = app_client()
    response = post_json(
        client,
        "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/handoff-index/export.zip",
        {"index": archive_index()},
    )

    with zipfile.ZipFile(io.BytesIO(response.get_data())) as archive:
        assert set(archive.namelist()) == REQUIRED_FILES


def test_csrf_token_is_used_in_route_tests():
    client = app_client()
    response = post_json(client, "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/handoff-index/export", {"index": archive_index()})

    assert response.status_code == 200


def test_no_connector_execution_function_is_called(monkeypatch):
    import socmint.dossier_finalization_handoff_export_bundle_v7_5_8 as bundle_module

    def explode(*_args, **_kwargs):
        raise AssertionError("connector execution must not happen")

    monkeypatch.setattr(bundle_module, "execute_connector", explode, raising=False)
    client = app_client()
    response = post_json(client, "/api/v1/dossier-builder/v3/intelligence/finalization/certificate/handoff-index/export", {"index": archive_index()})

    assert response.status_code == 200
    assert response.get_json()["recommended_action"] == "archive_ready"
